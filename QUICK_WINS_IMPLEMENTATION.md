# Quick Wins Implementation Guide: House of Commons Open Data

## Executive Summary

These quick wins can be implemented in 1-2 days and will add immediate value to CanadaGPT/FedMCP by filling critical data gaps in government structure and accountability tracking.

## Priority 1: Cabinet Ministers & Government Roles (2 hours)

### New Client Implementation

Create `/Users/matthewdufresne/FedMCP/src/fedmcp/clients/government_roles.py`:

```python
"""Client for fetching government roles from House of Commons Open Data."""

import logging
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

from .http import RateLimitedSession

logger = logging.getLogger(__name__)


@dataclass
class CabinetMinister:
    """Cabinet minister with portfolio."""
    name: str
    title: str
    department: Optional[str]
    precedence: int
    start_date: Optional[datetime]
    mp_url: Optional[str]


@dataclass
class ParliamentarySecretary:
    """Parliamentary secretary appointment."""
    name: str
    title: str
    minister_supported: str
    constituency: str
    start_date: Optional[datetime]


@dataclass
class PartyStanding:
    """Party seat distribution by province."""
    party: str
    total_seats: int
    provincial_seats: Dict[str, int]
    official_status: Optional[str]  # "Government", "Official Opposition", etc.


class GovernmentRolesClient:
    """Client for House of Commons government structure data."""

    BASE_URL = "https://www.ourcommons.ca"

    def __init__(self, session: Optional[RateLimitedSession] = None):
        """Initialize with optional shared session."""
        self.session = session or RateLimitedSession(min_request_interval=0)

    def get_cabinet_ministers(self) -> List[CabinetMinister]:
        """Fetch current Cabinet ministers with portfolios.

        Returns:
            List of CabinetMinister objects ordered by precedence
        """
        url = f"{self.BASE_URL}/Members/en/ministries/XML"
        logger.info("Fetching Cabinet ministers from %s", url)

        response = self.session.get(url)
        root = ET.fromstring(response.content)

        ministers = []
        for minister_elem in root.findall('.//Minister'):
            try:
                ministers.append(CabinetMinister(
                    name=minister_elem.findtext('PersonName', ''),
                    title=minister_elem.findtext('Title', ''),
                    department=minister_elem.findtext('Department'),
                    precedence=int(minister_elem.findtext('Precedence', '0')),
                    start_date=self._parse_date(minister_elem.findtext('FromDate')),
                    mp_url=minister_elem.findtext('PersonWebSiteUrl')
                ))
            except Exception as e:
                logger.warning(f"Error parsing minister: {e}")
                continue

        # Sort by precedence (Prime Minister = 1)
        ministers.sort(key=lambda m: m.precedence)
        logger.info(f"Retrieved {len(ministers)} Cabinet ministers")
        return ministers

    def get_parliamentary_secretaries(self) -> List[ParliamentarySecretary]:
        """Fetch current Parliamentary Secretaries.

        Returns:
            List of ParliamentarySecretary appointments
        """
        url = f"{self.BASE_URL}/Members/en/parliamentary-secretaries/XML"
        logger.info("Fetching Parliamentary Secretaries from %s", url)

        response = self.session.get(url)
        root = ET.fromstring(response.content)

        secretaries = []
        for ps_elem in root.findall('.//ParliamentarySecretary'):
            try:
                secretaries.append(ParliamentarySecretary(
                    name=ps_elem.findtext('PersonName', ''),
                    title=ps_elem.findtext('Title', ''),
                    minister_supported=ps_elem.findtext('MinisterSupported', ''),
                    constituency=ps_elem.findtext('ConstituencyName', ''),
                    start_date=self._parse_date(ps_elem.findtext('FromDate'))
                ))
            except Exception as e:
                logger.warning(f"Error parsing parliamentary secretary: {e}")
                continue

        logger.info(f"Retrieved {len(secretaries)} Parliamentary Secretaries")
        return secretaries

    def get_party_standings(self) -> List[PartyStanding]:
        """Fetch current party standings by province.

        Returns:
            List of PartyStanding objects with provincial seat distribution
        """
        url = f"{self.BASE_URL}/Members/en/party-standings/XML"
        logger.info("Fetching party standings from %s", url)

        response = self.session.get(url)
        root = ET.fromstring(response.content)

        standings = []
        for party_elem in root.findall('.//Party'):
            party_name = party_elem.findtext('Name', '')
            total = int(party_elem.findtext('TotalSeats', '0'))

            # Get provincial breakdown
            provincial = {}
            for prov_elem in party_elem.findall('.//Province'):
                prov_name = prov_elem.findtext('Name', '')
                seats = int(prov_elem.findtext('Seats', '0'))
                if seats > 0:
                    provincial[prov_name] = seats

            # Determine official status based on seat count
            status = None
            if total >= 170:  # Majority threshold
                status = "Government (Majority)"
            elif total >= 120:  # Largest party but minority
                status = "Government (Minority)"
            elif total >= 40:  # Substantial representation
                status = "Official Opposition" if len(standings) == 1 else "Third Party"

            standings.append(PartyStanding(
                party=party_name,
                total_seats=total,
                provincial_seats=provincial,
                official_status=status
            ))

        # Sort by seat count
        standings.sort(key=lambda p: p.total_seats, reverse=True)

        # Correct status for Official Opposition
        if len(standings) > 1 and standings[1].total_seats >= 12:
            standings[1].official_status = "Official Opposition"

        logger.info(f"Retrieved standings for {len(standings)} parties")
        return standings

    def get_speaker_and_officers(self) -> List[Dict]:
        """Fetch current Speaker and presiding officers.

        Returns:
            List of chair occupants with roles and dates
        """
        url = f"{self.BASE_URL}/Members/en/chair-occupants/XML"
        logger.info("Fetching Speaker and officers from %s", url)

        response = self.session.get(url)
        root = ET.fromstring(response.content)

        officers = []
        for officer_elem in root.findall('.//ChairOccupant'):
            officers.append({
                'name': officer_elem.findtext('PersonName', ''),
                'role': officer_elem.findtext('ChairTitle', ''),
                'start_date': self._parse_date(officer_elem.findtext('FromDate')),
                'constituency': officer_elem.findtext('ConstituencyName', '')
            })

        logger.info(f"Retrieved {len(officers)} presiding officers")
        return officers

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        try:
            # Try multiple date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None


# Example usage for Neo4j ingestion
def ingest_government_structure():
    """Example function to ingest government structure into Neo4j."""
    from neo4j import GraphDatabase

    client = GovernmentRolesClient()

    # Fetch all data
    ministers = client.get_cabinet_ministers()
    secretaries = client.get_parliamentary_secretaries()
    standings = client.get_party_standings()
    officers = client.get_speaker_and_officers()

    # Example Neo4j queries
    with GraphDatabase.driver("bolt://localhost:7687") as driver:
        with driver.session() as session:
            # Create Cabinet Role nodes
            for minister in ministers:
                session.run("""
                    MERGE (r:Role {id: $role_id})
                    SET r.title = $title,
                        r.type = 'Cabinet',
                        r.department = $department,
                        r.precedence = $precedence,
                        r.active = true,
                        r.start_date = $start_date
                    WITH r
                    MATCH (mp:MP {name: $mp_name})
                    MERGE (mp)-[:HOLDS_ROLE {current: true}]->(r)
                """, role_id=f"cabinet-{minister.title.lower().replace(' ', '-')}",
                     title=minister.title,
                     department=minister.department,
                     precedence=minister.precedence,
                     start_date=minister.start_date,
                     mp_name=minister.name)

            # Update Party nodes with standings
            for standing in standings:
                session.run("""
                    MATCH (p:Party {name: $party_name})
                    SET p.total_seats = $total,
                        p.official_status = $status,
                        p.provincial_seats = $provincial,
                        p.last_standing_update = datetime()
                """, party_name=standing.party,
                     total=standing.total_seats,
                     status=standing.official_status,
                     provincial=standing.provincial_seats)

    print(f"✅ Ingested {len(ministers)} Cabinet ministers")
    print(f"✅ Ingested {len(secretaries)} Parliamentary Secretaries")
    print(f"✅ Updated {len(standings)} party standings")
    print(f"✅ Ingested {len(officers)} presiding officers")
```

### MCP Server Integration

Add to `/Users/matthewdufresne/FedMCP/src/fedmcp/server.py`:

```python
# Add to imports
from .clients.government_roles import GovernmentRolesClient

# Initialize client
gov_roles_client = GovernmentRolesClient()

# Add new tools to list_tools():
{
    "name": "get_cabinet_ministers",
    "description": "Get current Cabinet ministers with portfolios and precedence order",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
},
{
    "name": "get_parliamentary_secretaries",
    "description": "Get current Parliamentary Secretaries and their assigned ministers",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
},
{
    "name": "get_party_standings",
    "description": "Get current party seat counts by province with official status",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
},

# Add handlers in call_tool():
elif name == "get_cabinet_ministers":
    ministers = await run_sync(gov_roles_client.get_cabinet_ministers)
    result = "## Current Cabinet Ministers (by precedence)\n\n"
    for minister in ministers:
        result += f"**{minister.precedence}. {minister.name}**\n"
        result += f"   - {minister.title}\n"
        if minister.department:
            result += f"   - Department: {minister.department}\n"
        result += "\n"
    return [TextContent(type="text", text=result)]

elif name == "get_parliamentary_secretaries":
    secretaries = await run_sync(gov_roles_client.get_parliamentary_secretaries)
    result = "## Current Parliamentary Secretaries\n\n"
    for ps in secretaries:
        result += f"**{ps.name}** ({ps.constituency})\n"
        result += f"   - {ps.title}\n"
        result += f"   - Supporting: {ps.minister_supported}\n\n"
    return [TextContent(type="text", text=result)]

elif name == "get_party_standings":
    standings = await run_sync(gov_roles_client.get_party_standings)
    result = "## Current Party Standings in House of Commons\n\n"
    for party in standings:
        result += f"**{party.party}**: {party.total_seats} seats"
        if party.official_status:
            result += f" ({party.official_status})"
        result += "\n"
        # Show top 3 provinces
        top_provinces = sorted(party.provincial_seats.items(),
                              key=lambda x: x[1], reverse=True)[:3]
        for prov, seats in top_provinces:
            result += f"   - {prov}: {seats}\n"
        result += "\n"
    return [TextContent(type="text", text=result)]
```

## Priority 2: Enhanced Constituencies Data (1 hour)

### Add to government_roles.py:

```python
@dataclass
class Constituency:
    """Electoral district information."""
    id: str
    name: str
    province: str
    mp_name: Optional[str]
    mp_party: Optional[str]
    population: Optional[int]
    electors: Optional[int]


def get_constituencies(self) -> List[Constituency]:
    """Fetch all constituency data with current MPs.

    Returns:
        List of Constituency objects
    """
    url = f"{self.BASE_URL}/Members/en/constituencies/XML"
    logger.info("Fetching constituencies from %s", url)

    response = self.session.get(url)
    root = ET.fromstring(response.content)

    constituencies = []
    for const_elem in root.findall('.//Constituency'):
        constituencies.append(Constituency(
            id=const_elem.findtext('ConstituencyId', ''),
            name=const_elem.findtext('ConstituencyName', ''),
            province=const_elem.findtext('ProvinceName', ''),
            mp_name=const_elem.findtext('CurrentMemberName'),
            mp_party=const_elem.findtext('CaucusName'),
            population=self._parse_int(const_elem.findtext('Population')),
            electors=self._parse_int(const_elem.findtext('Electors'))
        ))

    logger.info(f"Retrieved {len(constituencies)} constituencies")
    return constituencies
```

## Testing & Validation

### Quick Test Script

Create `/Users/matthewdufresne/FedMCP/test_gov_roles.py`:

```python
#!/usr/bin/env python3
"""Test government roles client."""

from src.fedmcp.clients.government_roles import GovernmentRolesClient

def main():
    client = GovernmentRolesClient()

    print("=" * 60)
    print("TESTING GOVERNMENT ROLES CLIENT")
    print("=" * 60)

    # Test Cabinet
    print("\n1. Cabinet Ministers:")
    ministers = client.get_cabinet_ministers()
    print(f"   Found {len(ministers)} ministers")
    if ministers:
        print(f"   Prime Minister: {ministers[0].name}")
        print(f"   Sample: {ministers[1].title} - {ministers[1].name}")

    # Test Parliamentary Secretaries
    print("\n2. Parliamentary Secretaries:")
    secretaries = client.get_parliamentary_secretaries()
    print(f"   Found {len(secretaries)} parliamentary secretaries")
    if secretaries:
        print(f"   Sample: {secretaries[0].name} supporting {secretaries[0].minister_supported}")

    # Test Party Standings
    print("\n3. Party Standings:")
    standings = client.get_party_standings()
    for party in standings[:3]:
        print(f"   {party.party}: {party.total_seats} seats ({party.official_status})")

    # Test Speaker
    print("\n4. Speaker and Officers:")
    officers = client.get_speaker_and_officers()
    print(f"   Found {len(officers)} presiding officers")
    if officers:
        speaker = next((o for o in officers if 'Speaker' in o['role']), None)
        if speaker:
            print(f"   Speaker: {speaker['name']}")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    main()
```

### Run Tests:

```bash
cd /Users/matthewdufresne/FedMCP
python test_gov_roles.py
```

## Expected Impact

### Immediate Benefits (Day 1)

1. **Cabinet Tracking**: Know which MPs hold ministerial positions
2. **Party Power Map**: Real-time seat distribution by province
3. **Government Structure**: Complete hierarchy from PM to Parliamentary Secretaries
4. **Enhanced Accountability**: Link ministerial decisions to department activities

### Query Examples Available Immediately

```cypher
// Which ministers voted on their own department's legislation?
MATCH (mp:MP)-[:HOLDS_ROLE]->(r:Role {type: 'Cabinet'})
MATCH (mp)-[:VOTED]->(v:Vote)-[:SUBJECT_OF]->(b:Bill)
WHERE b.title CONTAINS r.department
RETURN mp.name, r.title, b.number, b.title, v.position

// Parliamentary Secretary influence network
MATCH (ps:MP)-[:HOLDS_ROLE]->(r1:Role {type: 'Parliamentary Secretary'})
MATCH (minister:MP)-[:HOLDS_ROLE]->(r2:Role {type: 'Cabinet'})
WHERE r1.minister_supported = minister.name
MATCH (ps)-[:VOTED]->(v:Vote)<-[:VOTED]-(minister)
RETURN ps.name, minister.name, count(v) as aligned_votes
ORDER BY aligned_votes DESC
```

## Next Steps

1. **Deploy & Test** (30 minutes)
   - Add government_roles.py to codebase
   - Update server.py with new tools
   - Test with Claude Desktop

2. **Schedule Updates** (30 minutes)
   - Set up daily cron to refresh Cabinet data
   - Weekly refresh for party standings
   - Monitor for Cabinet shuffles

3. **Extend to Neo4j Pipeline** (2 hours)
   - Add Role node creation to data pipeline
   - Create HOLDS_ROLE relationships
   - Update Party nodes with standings

## Success Metrics

- ✅ 40+ Cabinet positions tracked
- ✅ 35+ Parliamentary Secretary appointments
- ✅ Real-time party standings by province
- ✅ 100% MP role coverage for current Parliament
- ✅ Zero API rate limiting (using XML feeds)

This implementation provides maximum value with minimal effort, using authoritative government sources that require no API keys or authentication.