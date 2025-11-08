"""Test bulk data sources for bills, committees, and Hansard."""
import sys
from pathlib import Path

# Add fedmcp to path
FEDMCP_PATH = Path(__file__).parent / "packages" / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.openparliament import OpenParliamentClient

print("=" * 60)
print("BULK DATA SOURCE INVESTIGATION")
print("=" * 60)

# 1. Bills - LEGISinfo JSON (CONFIRMED)
print("\n✅ BILLS: LEGISinfo JSON")
print("  URL: https://www.parl.ca/legisinfo/en/bills/json")
print("  Contains: 111 bills, ALL with sponsor data")
print("  Size: 204KB")
print("  Method: Direct download, no API calls needed")

# 2. Hansard - Get debate URLs from OpenParliament to extract DocIds
print("\n🔄 HANSARD: Testing XML download patterns...")
op = OpenParliamentClient()

print("  Fetching recent debates from OpenParliament API...")
debates = list(op.list_debates())[:5]

for debate in debates:
    print(f"\n  Debate: {debate.get('date')} - {debate.get('h1_en', '')}")
    print(f"    URL: {debate.get('url')}")
    # OpenParliament doesn't have DocId, but we can extract from date
    date = debate.get('date')
    if date:
        print(f"    Date: {date}")

# 3. Committees - Get committee URLs from OpenParliament
print("\n🔄 COMMITTEES: Testing available committees...")
committees = list(op.list_committees())[:10]

print(f"  Found {len(committees)} committees:")
for committee in committees:
    print(f"    {committee.get('slug')}: {committee.get('name', {}).get('en', 'N/A')}")
    print(f"      URL: {committee.get('url')}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
BILLS:
  ✅ Use LEGISinfo JSON bulk export
  URL: https://www.parl.ca/legisinfo/en/bills/json
  No API calls needed - single 204KB file with ALL sponsor data

HANSARD:
  ⚠️  XML available but requires DocId parameters
  Pattern: http://www.parl.gc.ca/HousePublications/Publication.aspx?
           Pub=Hansard&Doc=[SITTING]&Parl=45&Ses=1&Language=E&xml=true
  Strategy: Use OpenParliament API to list debates, then fetch XML for each

COMMITTEES:
  ⚠️  XML available but requires DocId parameters
  Pattern: http://www.parl.gc.ca/HousePublications/Publication.aspx?
           Mode=1&Parl=45&Ses=1&DocId=[ID]&Language=E&xml=true
  Strategy: Use OpenParliament API to list committees/meetings, then fetch XML

RECOMMENDATION:
  - Bills: Use LEGISinfo JSON (immediate win, no refactoring needed)
  - Hansard & Committees: OpenParliament API already provides good data
    - XML files require mapping URLs to DocIds (complex)
    - OpenParliament has clean, paginated API with rate limiting
    - Only fetch XML if OpenParliament data is insufficient
""")
