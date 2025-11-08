"""Test what get_bill() returns from OpenParliament API."""
import sys
from pathlib import Path

FEDMCP_PATH = Path(__file__).parent / "packages" / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.openparliament import OpenParliamentClient

client = OpenParliamentClient()

print("Testing individual bill detail from OpenParliament API...")
print("=" * 60)

# Test a recent bill
try:
    # Get first bill from list
    first_bill = next(client.list_bills())
    number = first_bill.get("number")
    session = first_bill.get("session")
    bill_url = first_bill.get("url")

    print(f"Testing bill: {number} ({session})")
    print(f"Bill URL: {bill_url}")
    print(f"From list endpoint - sponsor_politician_url: {first_bill.get('sponsor_politician_url')}")

    # Now fetch the full bill detail using the URL
    bill_detail = client.get_bill(bill_url)

    print("\nFull bill detail fields:")
    for key in sorted(bill_detail.keys()):
        value = bill_detail.get(key)
        if 'sponsor' in key.lower():
            print(f"  ★ {key}: {value}")
        else:
            # Truncate long values
            if isinstance(value, str) and len(value) > 50:
                print(f"  {key}: {value[:50]}...")
            elif isinstance(value, dict):
                print(f"  {key}: {{...}}")
            elif isinstance(value, list):
                print(f"  {key}: [{len(value)} items]")
            else:
                print(f"  {key}: {value}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
