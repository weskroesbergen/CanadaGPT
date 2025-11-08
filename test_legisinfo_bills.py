"""Test what LEGISinfo bulk exports provide for bills."""
import sys
from pathlib import Path

FEDMCP_PATH = Path(__file__).parent / "packages" / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.legisinfo import LegisInfoClient

client = LegisInfoClient()

print("Testing LEGISinfo bulk bill exports...")
print("=" * 60)

# Get bills from current parliament (45th parliament)
try:
    bills = client.list_bills()

    print(f"Total bills available: {len(bills)}")

    # Sample first bill
    if bills:
        first_bill = bills[0]
        print("\nFirst bill fields:")
        for key in sorted(first_bill.keys()):
            value = first_bill.get(key)
            if 'sponsor' in key.lower() or 'mp' in key.lower() or 'member' in key.lower():
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

        # Check if we have sponsor info
        print("\n" + "=" * 60)
        sponsor_count = sum(1 for b in bills[:100] if 'SponsorPersonOfficialFirstName' in b or 'sponsor' in str(b).lower())
        print(f"Bills with sponsor data (first 100): {sponsor_count}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
