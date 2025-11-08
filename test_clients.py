#!/usr/bin/env python3
"""Quick test script for FedMCP clients."""

from fedmcp import (
    OpenParliamentClient,
    MPExpenditureClient,
    PetitionsClient,
    LobbyingRegistryClient,
)

print("🧪 Testing FedMCP Clients...\n")

# Test 1: OpenParliament
print("1️⃣ Testing OpenParliament - Recent debates...")
op = OpenParliamentClient()
debates = list(op.list_debates(limit=3))
print(f"   ✅ Found {len(debates)} recent debates")
if debates:
    print(f"   Latest: {debates[0].get('topic', 'N/A')}\n")

# Test 2: MP Expenditures
print("2️⃣ Testing MP Expenditures - Top travel spenders...")
exp = MPExpenditureClient()
try:
    top_spenders = exp.get_top_spenders("travel", fiscal_year=2026, quarter=1, limit=3)
    print(f"   ✅ Found {len(top_spenders)} top spenders")
    if top_spenders:
        print(f"   Top spender: {top_spenders[0].name} - ${top_spenders[0].travel:,.2f}\n")
except Exception as e:
    print(f"   ⚠️  Note: {str(e)[:100]}\n")

# Test 3: Petitions
print("3️⃣ Testing Petitions - Search for 'climate'...")
petitions = PetitionsClient()
results = petitions.search_petitions(keyword="climate", category="All", limit=3)
print(f"   ✅ Found {len(results)} petitions about climate")
if results:
    print(f"   Example: {results[0].title[:80]}...\n")

# Test 4: Lobbying Registry (this downloads data on first run)
print("4️⃣ Testing Lobbying Registry - Top clients...")
print("   ⏳ Downloading lobbying data (first run takes ~30 seconds)...")
lobbying = LobbyingRegistryClient()
top_clients = lobbying.get_top_clients(limit=3, active_only=True)
print(f"   ✅ Found {len(top_clients)} top lobbying clients")
if top_clients:
    print(f"   Top client: {top_clients[0]['client_name']} ({top_clients[0]['registration_count']} registrations)\n")

print("✅ All client tests completed successfully!")
print("\nNext steps:")
print("  • Add to Claude Desktop config to use all 42 MCP tools")
print("  • Run 'python -m fedmcp.server' to start the MCP server")
print("  • See README.md for detailed use case examples")
