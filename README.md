# FedMCP - Canadian Government Accountability Platform

A comprehensive MCP (Model Context Protocol) server providing **deep access** to Canadian federal parliamentary, legal, and accountability data through Claude and other LLM applications.

**42 tools** | **8 data sources** | **Full government accountability** | **Advanced analytics**

## 🎯 What is FedMCP?

FedMCP is a research and transparency platform that gives you unprecedented access to Canadian government data:

- Track **who is lobbying** government and on what issues
- Monitor **MP expenses** and spending patterns
- Follow **citizen petitions** and government responses
- Search **parliamentary debates** and voting records
- Analyze **legislative progress** and bill sponsorship
- Browse **Canadian case law** and legal precedents
- Detect **conflicts of interest** through cross-source analysis
- Compare **MP performance** across multiple accountability metrics

Perfect for journalists, researchers, activists, and engaged citizens.

## 📊 Data Sources (8 Total)

1. **OpenParliament API** - Debates, votes, MPs, bills, committees
2. **House of Commons Hansard** - Official parliamentary transcripts
3. **LEGISinfo** - Legislative tracking and bill details
4. **CanLII API** - Canadian case law and legislation (requires free API key)
5. **Represent API** - Postal code to MP lookup
6. **MP Expenditures** - Quarterly proactive disclosure data
7. **House Petitions** - Citizen petitions and government responses
8. **Lobbying Registry** - Federal lobbying registrations and communications (100,000+ records)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/northernvariables/FedMCP.git
cd FedMCP

# Install in development mode
pip install -e .
```

### Configuration

For CanLII access, obtain a free API key:
1. Request key from https://www.canlii.org/en/feedback/feedback.html
2. Add to environment:

```bash
cp .env.example .env
# Edit .env and add: CANLII_API_KEY=your_key_here
```

### Claude Desktop Setup

Add to your configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "fedmcp": {
      "command": "python",
      "args": ["-m", "fedmcp.server"],
      "env": {
        "CANLII_API_KEY": "your_key_here"
      }
    }
  }
}
```

Restart Claude Desktop and the FedMCP tools will appear in your MCP tools menu.

## 🔧 Available Tools (42 Total)

### Parliamentary Data (17 tools)
- `search_debates` - Search House debates by keyword
- `list_debates` - List recent debates with temporal filtering
- `search_bills` - Search bills by number or keywords
- `get_bill` - Get specific bill details from LEGISinfo
- `list_bills` - List bills with filtering options
- `get_bill_votes` - Get all votes on a specific bill
- `list_mps` - List Members of Parliament with filters
- `search_politician` - Search for MPs and Senators by name
- `get_politician_voting_history` - Get complete voting records
- `list_votes` - List parliamentary votes with filtering
- `get_vote_details` - Get detailed vote info with individual ballots
- `list_committees` - List parliamentary committees
- `get_committee_details` - Get committee meetings and members
- `find_mp_by_postal_code` - Find your MP by postal code
- `search_hansard` - Search Hansard transcripts for quotes
- `get_hansard_sitting` - Get complete sitting transcript
- `search_topic_across_sources` - Search across bills, debates, votes, Hansard

### MP Accountability (11 tools)
- `get_mp_expenses` - Get MP quarterly expenditure data
- `search_mp_expenses` - Search expenses by name/party/constituency
- `get_top_mp_spenders` - Rank MPs by spending category
- `get_party_spending_averages` - Compare party spending patterns
- `get_mp_activity_scorecard` - Comprehensive MP performance metrics
- `analyze_mp_bills` - Analyze MP legislative record and success rate
- `compare_mp_performance` - Side-by-side comparison of 2-5 MPs
- `analyze_mp_voting_participation` - Voting attendance and patterns
- `analyze_party_discipline` - Find MPs who voted against party line
- `get_bill_legislative_progress` - Track bill journey through Parliament
- `detect_conflicts_of_interest` - Cross-reference expenses, lobbying, voting

### Petitions (2 tools)
- `search_petitions` - Search citizen petitions by keyword/sponsor
- `get_petition_details` - Get petition with government response

### Lobbying & Influence (5 tools)
- `search_lobbying_registrations` - Search active lobbying registrations
- `search_lobbying_communications` - Find reported lobbying meetings
- `get_top_lobbying_clients` - Rank organizations by lobbying activity
- `analyze_bill_lobbying` - See who's lobbying on specific bills
- `analyze_industry_influence` - Industry-wide lobbying analysis

### Analytics (1 tool)
- `track_committee_activity` - Analyze committee productivity and focus

### Legal Data (5 tools - requires CanLII API key)
- `search_cases` - Search case law by database and keywords
- `get_case` - Get case metadata
- `get_case_citations` - Get citing/cited cases and legislation
- `search_legislation` - Browse federal and provincial legislation
- `list_legal_databases` - List available court/tribunal databases

## 💡 Use Case Examples

### 🔍 Investigating Corporate Influence

**Scenario:** You want to know who's lobbying on Bill C-11 (Online Streaming Act)

```
1. User: "What organizations are lobbying on Bill C-11?"
   Tool: analyze_bill_lobbying(bill_code="c-11", parliament_session="44-1")
   → Returns list of organizations, lobbyists, meeting counts

2. User: "Show me the actual lobbying communications about C-11"
   Tool: search_lobbying_communications(subject_keyword="c-11 online streaming")
   → Returns meeting dates, government officials met, specific topics

3. User: "How did MPs vote on C-11?"
   Tool: get_bill_votes(bill_code="c-11")
   → Returns all votes with individual MP ballots

4. User: "Check for conflicts of interest"
   Tool: detect_conflicts_of_interest(politician_name="[MP Name]", date_range_months=12)
   → Cross-references their votes, lobbying meetings, and expenses
```

### 📊 MP Performance Analysis

**Scenario:** Comparing your MP to others in the same party

```
User: "Compare the performance of Chrystia Freeland and Mark Holland"
Tool: compare_mp_performance(mp_names=["Chrystia Freeland", "Mark Holland"])

Returns:
- Bills sponsored and success rates
- Voting participation rates
- Committee memberships
- Petition sponsorships
- Quarterly expenses by category
- Recent lobbying communications
- Side-by-side performance metrics
```

### 🗳️ Tracking Citizen Engagement

**Scenario:** Following petition activity on climate change

```
1. User: "Show me active petitions about climate change"
   Tool: search_petitions(keyword="climate change", category="Open", limit=20)
   → Returns open petitions with signature counts

2. User: "Get details on petition e-4519"
   Tool: get_petition_details(petition_number="e-4519")
   → Returns full petition text, sponsor, signatures by province, status

3. User: "Has the government responded?"
   → Shows government response text if available
```

### 💰 Expense Monitoring

**Scenario:** Analyzing MP spending patterns

```
1. User: "Who are the top spenders on travel this quarter?"
   Tool: get_top_mp_spenders(category="travel", fiscal_year=2026, quarter=1, limit=10)
   → Ranks MPs by travel expenses

2. User: "Compare average spending by party"
   Tool: get_party_spending_averages(fiscal_year=2026, quarter=1)
   → Shows Liberal vs Conservative vs NDP vs etc. average expenses

3. User: "Show me expenses for Pierre Poilievre"
   Tool: search_mp_expenses(name="Pierre Poilievre", fiscal_year=2026, quarter=1)
   → Returns detailed breakdown: salaries, travel, hospitality, contracts
```

### 🏛️ Legislative Research

**Scenario:** Understanding a bill's journey through Parliament

```
1. User: "What's the current status of Bill C-3?"
   Tool: get_bill_legislative_progress(bill_code="c-3", parliament_session="44-1")
   → Shows: current stage, all completed stages, timeline, sponsor

2. User: "Who sponsored this bill and what else have they sponsored?"
   Tool: analyze_mp_bills(politician_name="[Sponsor Name]", limit=20)
   → Returns MP's legislative record, success rate, bill topics

3. User: "Search for related debates"
   Tool: search_topic_across_sources(keyword="Bill C-3", limit=10)
   → Searches bills, debates, votes, Hansard in one query
```

### ⚖️ Legal Research

**Scenario:** Finding case law on Charter rights

```
1. User: "Find Supreme Court cases about section 7 of the Charter"
   Tool: search_cases(database_id="csc-scc", keyword="section 7 charter life liberty security", limit=10)
   → Returns recent SCC decisions

2. User: "Get details on R. v. Jordan"
   Tool: get_case(database_id="csc-scc", case_id="2016scc27")
   → Returns full case metadata, date, judges, subject areas

3. User: "What cases have cited R. v. Jordan?"
   Tool: get_case_citations(database_id="csc-scc", case_id="2016scc27", citing_cases=True)
   → Returns all cases that have cited this precedent
```

### 🔴 Corruption Detection

**Scenario:** Identifying unusual patterns

```
User: "Generate a full activity scorecard for MP [Name]"
Tool: get_mp_activity_scorecard(politician_name="[Name]")

Returns comprehensive report:
- Bills sponsored (count, topics, success rate)
- Petitions sponsored
- Voting participation rate
- Recent votes cast
- Quarterly expenses breakdown
- Recent lobbying communications with this MP
- Red flags: unusual spending, frequent lobbying meetings, voting anomalies
```

## 🏗️ Architecture

### Client Structure

All clients follow consistent patterns with built-in rate limiting and retry logic:

- **OpenParliamentClient** (`clients/openparliament.py`) - Pagination-aware API client with automatic next-page fetching
- **OurCommonsHansardClient** (`clients/ourcommons.py`) - XML parser for Hansard transcripts with UTF-8 BOM handling
- **LegisInfoClient** (`clients/legisinfo.py`) - Access to LEGISinfo bill and legislation data
- **CanLIIClient** (`clients/canlii.py`) - REST API with 2 req/sec rate limiting (0.5s minimum interval)
- **RepresentClient** (`clients/represent.py`) - Postal code lookup via Open North API
- **MPExpenditureClient** (`clients/expenditure.py`) - House of Commons proactive disclosure data
- **PetitionsClient** (`clients/petitions.py`) - XML API for petition data with client-side filtering
- **LobbyingRegistryClient** (`clients/lobbying.py`) - Downloads and caches federal lobbying data (~90MB)

### Rate Limiting

All HTTP clients use `RateLimitedSession` with:
- **Proactive rate limiting:** Configurable minimum interval between requests
- **Reactive retry logic:** Exponential backoff for 429/5xx errors
- **Automatic retries:** Up to 5 attempts with increasing delays

### Caching Strategy

**Lobbying Registry:**
- Downloads 100,000+ records (~90MB compressed) on first use
- Cached at `~/.cache/fedmcp/lobbying/`
- Optional auto-update after 7 days
- Instant loading on subsequent uses

## 📈 Recent Enhancements

### Phase 8: Advanced Analytics (November 2025) 🆕
- ✅ **Industry Influence Analysis** - Track corporate lobbying across entire industries
- ✅ **MP Performance Comparison** - Side-by-side metrics for 2-5 MPs
- ✅ **Cross-source accountability** engine with 42 total tools

### Phase 7: Multi-Source Correlation (November 2025) 🆕
- ✅ **MP Activity Scorecard** - Comprehensive metrics from 6+ data sources
- ✅ **Committee Activity Tracking** - Productivity and focus analysis
- ✅ **Conflict of Interest Detection** - Cross-reference expenses, lobbying, voting

### Phase 6: Bill Analysis (November 2025)
- ✅ **MP Bill Analysis** - Legislative record and success rates
- ✅ **Party Bill Comparison** - Compare party legislative effectiveness
- ✅ **Bill Progress Tracking** - Detailed timeline through Parliament

### Phase 5: Lobbying Registry (November 2025)
- ✅ **Lobbying Search** - 100,000+ registrations, 350,000+ communications
- ✅ **Top Clients Analysis** - Rank organizations by lobbying activity
- ✅ **Bill Lobbying Analysis** - See who's lobbying on specific bills
- ✅ **Latin-1 encoding** support for Canadian government CSV data

### Phase 4: Petitions System (November 2025)
- ✅ **Petition Search** - 341+ active petitions with keyword search
- ✅ **Government Response Tracking** - Full petition text and official responses
- ✅ **Client-side filtering** for comprehensive search

### Phase 3: MP Expenditures (November 2025)
- ✅ **Quarterly Expense Data** - Salaries, travel, hospitality, contracts
- ✅ **Top Spenders Analysis** - Rank MPs by spending category
- ✅ **Party Spending Averages** - Compare party spending patterns

### Phase 2: Enhanced Parliamentary Tools (November 2025)
- ✅ **Postal Code to MP Lookup** - #1 most requested citizen feature
- ✅ **Party Discipline Analysis** - Identify MPs voting against party line
- ✅ **Committee Data Access** - List committees, get meeting details
- ✅ **Temporal Filtering** - Date ranges for votes and debates

### Phase 1: Foundational Features (November 2025)
- ✅ Politician search by name
- ✅ Voting history and participation analysis
- ✅ Full Hansard sitting transcripts
- ✅ Enhanced debate/MP/vote listings

**Total Growth:** From initial 14 tools to **42 tools (+200%)** with **full government accountability** coverage.

## 🎓 For Developers

### Testing Client Usage

```python
import os
from fedmcp import (
    OpenParliamentClient,
    LegisInfoClient,
    OurCommonsHansardClient,
    CanLIIClient,
    MPExpenditureClient,
    PetitionsClient,
    LobbyingRegistryClient
)

# OpenParliament - pagination is automatic
op = OpenParliamentClient()
for debate in op.list_debates(limit=10):
    print(debate)

# LEGISinfo - session format is "parliament-session"
legis = LegisInfoClient()
bill = legis.get_bill("44-1", "c-11")

# MP Expenditures - fiscal year format
exp = MPExpenditureClient()
expenses = exp.get_top_spenders("travel", fiscal_year=2026, quarter=1, limit=10)

# Petitions - search with client-side filtering
petitions = PetitionsClient()
results = petitions.search_petitions(keyword="climate", category="All", limit=10)

# Lobbying - downloads and caches data on first use
lobbying = LobbyingRegistryClient(auto_update=True)
registrations = lobbying.search_registrations(
    client_name="Microsoft",
    active_only=True,
    limit=10
)

# CanLII - requires API key
canlii = CanLIIClient(api_key=os.getenv("CANLII_API_KEY"))
cases = canlii.search_cases_by_keyword("csc-scc", "charter rights", limit=10)
```

### Running Tests

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Adding New Tools

1. Define tool schema in `list_tools()` in `server.py`
2. Implement handler in `call_tool()` function
3. Return results as `TextContent` objects
4. Handle errors with try/except blocks
5. Update documentation in `CLAUDE.md`

## ⚠️ Important Notes

### Data Freshness
- **OpenParliament:** Real-time API (updated continuously)
- **Hansard:** Published daily after sittings
- **LEGISinfo:** Updated as bills progress through Parliament
- **MP Expenditures:** Published quarterly (90 days after quarter end)
- **Petitions:** Real-time API
- **Lobbying Registry:** Updated monthly (cached locally for 7 days)
- **CanLII:** Updated daily with new case law

### Rate Limits
- **OpenParliament:** 10 req/sec (conservative, API allows more)
- **CanLII:** 2 req/sec, 5,000 queries/day (enforced by API key)
- **All others:** No rate limiting required (static data or tolerant APIs)

### Data Limitations & Caveats

**MP Expenditure Data:**
- **Historical Limit:** Data only available from July 2020 (FY 2020-2021 Q2) onward
- **Missing Quarter:** FY 2020-2021 Q1 (Apr-Jun 2020) returns server errors - not available
- **Pre-2020 Data:** Not available through current proactive disclosure system (likely different format/archived)
- **Total Coverage:** ~4.5 years of expense data vs. 20+ year MP careers

**Travel Expense Reporting Nuances:**
- Party leader travel may be funded through:
  - Party budgets (not individual MP office budgets)
  - Research office allocations
  - Parliamentary precinct allowances
- MPs with ridings near Ottawa (e.g., Carleton, Ottawa-area) naturally have lower travel expenses
- COVID-19 pandemic (2020-2021) significantly reduced all travel expenses
- $0 travel expenses do NOT necessarily indicate no travel occurred - check expense category definitions

**Lobbying Registry:**
- First-time data download takes ~30 seconds (~90MB)
- Subsequent loads are instant (cached locally)
- Data updated monthly by Office of the Commissioner of Lobbying

### Privacy & Ethics
- All data is **publicly available** government information
- Designed for **transparency and accountability**, not harassment
- Use responsibly for **research, journalism, and civic engagement**
- Respect MP privacy for non-parliamentary activities
- Expense data represents office spending, not personal wealth or income

## ☁️ Deploying to Google Cloud

Want to move your Neo4j database to production on GCP? We've created a complete migration guide with automated scripts.

**See:** [GCP_MIGRATION_QUICKSTART.md](GCP_MIGRATION_QUICKSTART.md)

**What you get:**
- Automated migration scripts (8 steps, ~1 hour)
- Production-ready VM configuration (n2-standard-2, 8GB RAM)
- Daily automated backups to Google Cloud Storage
- Firewall rules and security best practices
- Cost: ~$50-65/month
- Full rollback capability

All scripts are in `scripts/gcp-migration/` - ready to run!

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Credits

- Based on canfedinfo library from broadcast-os project
- Uses Open North's Represent API for postal code lookup
- CanLII data courtesy of Canadian Legal Information Institute
- OpenParliament data from openparliament.ca
- Parliamentary data from House of Commons and Senate

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation (CLAUDE.md and README.md)
5. Submit a pull request

## 📧 Support

For bugs or feature requests, open an issue on GitHub.

For CanLII API key issues, contact https://www.canlii.org/en/feedback/feedback.html

---

**Built with ❤️ for Canadian democracy and government transparency**
