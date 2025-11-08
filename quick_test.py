#!/usr/bin/env python3
"""Quick test of FedMCP core functionality (no lobbying download)."""

print("🧪 Testing FedMCP Core Functionality...\n")

# Test 1: Import all clients
print("1️⃣ Testing imports...")
try:
    from fedmcp import (
        OpenParliamentClient,
        MPExpenditureClient,
        PetitionsClient,
        RepresentClient,
    )
    print("   ✅ All clients imported successfully\n")
except Exception as e:
    print(f"   ❌ Import failed: {e}\n")
    exit(1)

# Test 2: OpenParliament
print("2️⃣ Testing OpenParliament - Recent debates...")
try:
    op = OpenParliamentClient()
    debates = list(op.list_debates(limit=2))
    print(f"   ✅ Found {len(debates)} recent debates")
    if debates:
        print(f"   Latest: {debates[0].get('topic', 'N/A')[:60]}...\n")
except Exception as e:
    print(f"   ⚠️  Error: {str(e)[:100]}\n")

# Test 3: Petitions
print("3️⃣ Testing Petitions - Active petitions...")
try:
    petitions_client = PetitionsClient()
    results = petitions_client.list_petitions(category="Open", limit=2)
    print(f"   ✅ Found {len(results)} active petitions")
    if results:
        print(f"   Example: {results[0].title[:60]}...\n")
except Exception as e:
    print(f"   ⚠️  Error: {str(e)[:100]}\n")

# Test 4: Represent API
print("4️⃣ Testing Represent - Postal code lookup...")
try:
    represent = RepresentClient()
    mp = represent.find_mp_by_postal_code("K1A0A9")
    if mp:
        print(f"   ✅ Found MP: {mp.get('name', 'N/A')}")
        print(f"   Riding: {mp.get('district_name', 'N/A')}\n")
except Exception as e:
    print(f"   ⚠️  Error: {str(e)[:100]}\n")

print("✅ Core functionality tests completed!")
print("\n📝 Next Steps:")
print("  • To test lobbying: Run full test_clients.py (downloads 90MB data)")
print("  • To test MCP server: Run 'python -m fedmcp.server'")
print("  • To use in Claude Desktop: Add to config and restart Claude")
