#!/usr/bin/env python3
"""
Test GraphQL queries for Parliament and Session nodes.

This script tests:
1. currentParliament query
2. currentSession query
3. parliamentStats query
4. sessionStats query
5. Basic Parliament and Session queries
"""

import requests
import json
import sys

# GraphQL endpoint (assumes local development server running on port 4000)
GRAPHQL_ENDPOINT = "http://localhost:4000/graphql"
API_KEY = "21374cf579c3c6d470090cf408171d8fd4c77202c68572af598f3d72d1142dc4"  # PUBLIC_API_KEY

def run_query(query, variables=None):
    """Execute a GraphQL query and return the result."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    try:
        response = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error executing query: {e}")
        return None

def test_current_parliament():
    """Test currentParliament custom query."""
    print("=" * 80)
    print("TEST 1: currentParliament Query")
    print("=" * 80)

    query = """
    query {
      currentParliament {
        number
        ordinal
        election_date
        opening_date
        dissolution_date
        party_in_power
        prime_minister
        total_seats
        is_current
      }
    }
    """

    result = run_query(query)
    if result and "data" in result:
        parliament = result["data"]["currentParliament"]
        print(f"✓ Current Parliament: {parliament['ordinal']} Parliament")
        print(f"  Election Date: {parliament['election_date']}")
        print(f"  Prime Minister: {parliament['prime_minister']}")
        print(f"  Party: {parliament['party_in_power']}")
        print(f"  Total Seats: {parliament['total_seats']}")
        print(f"  Is Current: {parliament['is_current']}")
        return True
    else:
        print(f"✗ Query failed: {result}")
        return False

def test_current_session():
    """Test currentSession custom query."""
    print("\n" + "=" * 80)
    print("TEST 2: currentSession Query")
    print("=" * 80)

    query = """
    query {
      currentSession {
        id
        parliament_number
        session_number
        start_date
        end_date
        is_current
      }
    }
    """

    result = run_query(query)
    if result and "data" in result:
        session = result["data"]["currentSession"]
        print(f"✓ Current Session: {session['id']}")
        print(f"  Parliament: {session['parliament_number']}")
        print(f"  Session: {session['session_number']}")
        print(f"  Start Date: {session['start_date']}")
        print(f"  End Date: {session['end_date']}")
        print(f"  Is Current: {session['is_current']}")
        return True
    else:
        print(f"✗ Query failed: {result}")
        return False

def test_parliament_stats():
    """Test parliamentStats custom query for 45th Parliament."""
    print("\n" + "=" * 80)
    print("TEST 3: parliamentStats Query (45th Parliament)")
    print("=" * 80)

    query = """
    query($parliamentNumber: Int!) {
      parliamentStats(parliamentNumber: $parliamentNumber) {
        parliament {
          number
          ordinal
          election_date
          party_in_power
          prime_minister
        }
        bill_count
        vote_count
        document_count
        session_count
      }
    }
    """

    result = run_query(query, {"parliamentNumber": 45})
    if result and "data" in result:
        stats = result["data"]["parliamentStats"]
        print(f"✓ Stats for {stats['parliament']['ordinal']} Parliament:")
        print(f"  Bills: {stats['bill_count']}")
        print(f"  Votes: {stats['vote_count']}")
        print(f"  Documents: {stats['document_count']}")
        print(f"  Sessions: {stats['session_count']}")
        return True
    else:
        print(f"✗ Query failed: {result}")
        return False

def test_session_stats():
    """Test sessionStats custom query for Session 45-1."""
    print("\n" + "=" * 80)
    print("TEST 4: sessionStats Query (Session 45-1)")
    print("=" * 80)

    query = """
    query($sessionId: ID!) {
      sessionStats(sessionId: $sessionId) {
        session {
          id
          parliament_number
          session_number
          start_date
        }
        bill_count
        vote_count
        document_count
      }
    }
    """

    result = run_query(query, {"sessionId": "45-1"})
    if result and "data" in result:
        stats = result["data"]["sessionStats"]
        print(f"✓ Stats for Session {stats['session']['id']}:")
        print(f"  Start Date: {stats['session']['start_date']}")
        print(f"  Bills: {stats['bill_count']}")
        print(f"  Votes: {stats['vote_count']}")
        print(f"  Documents: {stats['document_count']}")
        return True
    else:
        print(f"✗ Query failed: {result}")
        return False

def test_parliament_list():
    """Test querying all parliaments."""
    print("\n" + "=" * 80)
    print("TEST 5: List All Parliaments")
    print("=" * 80)

    query = """
    query {
      parliaments(options: { limit: 5, sort: [{ number: DESC }] }) {
        number
        ordinal
        election_date
        prime_minister
      }
    }
    """

    result = run_query(query)
    if result and "data" in result:
        parliaments = result["data"]["parliaments"]
        print(f"✓ Retrieved {len(parliaments)} most recent parliaments:")
        for p in parliaments:
            print(f"  {p['ordinal']} - {p['prime_minister']} ({p['election_date']})")
        return True
    else:
        print(f"✗ Query failed: {result}")
        return False

def test_session_list():
    """Test querying all sessions."""
    print("\n" + "=" * 80)
    print("TEST 6: List All Sessions")
    print("=" * 80)

    query = """
    query {
      sessions(options: { limit: 5, sort: [{ id: DESC }] }) {
        id
        parliament_number
        session_number
        start_date
      }
    }
    """

    result = run_query(query)
    if result and "data" in result:
        sessions = result["data"]["sessions"]
        print(f"✓ Retrieved {len(sessions)} most recent sessions:")
        for s in sessions:
            print(f"  {s['id']} - Parliament {s['parliament_number']}, Session {s['session_number']} ({s['start_date']})")
        return True
    else:
        print(f"✗ Query failed: {result}")
        return False

def test_parliament_sessions_relationship():
    """Test Parliament-Session relationship."""
    print("\n" + "=" * 80)
    print("TEST 7: Parliament-Session Relationship")
    print("=" * 80)

    query = """
    query {
      parliaments(where: { number: 45 }) {
        number
        ordinal
        sessions {
          id
          start_date
          end_date
        }
      }
    }
    """

    result = run_query(query)
    if result and "data" in result:
        parliaments = result["data"]["parliaments"]
        if parliaments:
            p = parliaments[0]
            print(f"✓ {p['ordinal']} Parliament has {len(p['sessions'])} session(s):")
            for s in p['sessions']:
                print(f"  {s['id']}: {s['start_date']} - {s['end_date'] or 'ongoing'}")
            return True
        else:
            print("✗ No parliament found with number 45")
            return False
    else:
        print(f"✗ Query failed: {result}")
        return False

def main():
    """Run all tests."""
    print("PARLIAMENT & SESSION GRAPHQL TEST SUITE")
    print("Testing GraphQL endpoint: " + GRAPHQL_ENDPOINT)
    print("")

    tests = [
        test_current_parliament,
        test_current_session,
        test_parliament_stats,
        test_session_stats,
        test_parliament_list,
        test_session_list,
        test_parliament_sessions_relationship,
    ]

    results = []
    for test in tests:
        try:
            success = test()
            results.append(success)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
