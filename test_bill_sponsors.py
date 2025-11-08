"""Test if OpenParliament API returns bill sponsor data."""
import sys
from pathlib import Path

FEDMCP_PATH = Path(__file__).parent / "packages" / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.openparliament import OpenParliamentClient

client = OpenParliamentClient()

print("Testing bill sponsor data from OpenParliament API...")
print("=" * 60)

# Get first 10 bills
for i, bill in enumerate(client.list_bills()):
    if i >= 10:
        break

    number = bill.get("number", "N/A")
    session = bill.get("session", "N/A")
    sponsor_url = bill.get("sponsor_politician_url")
    sponsor_mp = bill.get("sponsor_mp")

    print(f"\nBill {number} ({session})")
    print(f"  Title: {bill.get('name', {}).get('en', 'N/A')[:50]}...")
    print(f"  sponsor_politician_url: {sponsor_url}")
    print(f"  sponsor_mp: {sponsor_mp}")

    # Check all keys that contain 'sponsor'
    sponsor_keys = [k for k in bill.keys() if 'sponsor' in k.lower()]
    if sponsor_keys:
        print(f"  All sponsor keys: {sponsor_keys}")

print("\n" + "=" * 60)
print("Summary: Checking if ANY bills have sponsor data...")

bills_with_sponsors = 0
bills_without_sponsors = 0

for i, bill in enumerate(client.list_bills()):
    if i >= 100:  # Check first 100 bills
        break

    if bill.get("sponsor_politician_url") or bill.get("sponsor_mp"):
        bills_with_sponsors += 1
    else:
        bills_without_sponsors += 1

print(f"Bills WITH sponsor data: {bills_with_sponsors}/100")
print(f"Bills WITHOUT sponsor data: {bills_without_sponsors}/100")
