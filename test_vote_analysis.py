"""
Test vote analysis queries on imported Neo4j data.

Verifies:
- Vote statistics and coverage
- MP voting patterns
- Party cohesion analysis
- Historical term analysis
- Dissenting votes
- Cross-source data linkage
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.home() / "FedMCP/packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
import os
from dotenv import load_dotenv

load_dotenv(Path.home() / "FedMCP/packages/data-pipeline/.env")

def main():
    print("=" * 80)
    print("VOTE ANALYSIS QUERY TESTS")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    neo4j = Neo4jClient(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD")
    )

    try:
        # Test 1: Basic vote statistics
        print("1. Basic Vote Statistics")
        print("-" * 40)
        stats = neo4j.run_query("""
            MATCH (v:Vote)
            OPTIONAL MATCH (mp:MP)-[cv:CAST_VOTE]->(v)
            RETURN
                count(DISTINCT v) as total_votes,
                count(cv) as total_cast_votes,
                count(DISTINCT mp) as mps_who_voted
        """)

        if stats:
            s = stats[0]
            print(f"   Total Vote events: {s['total_votes']:,}")
            print(f"   Total individual MP votes: {s['total_cast_votes']:,}")
            print(f"   MPs who have voted: {s['mps_who_voted']:,}")
            if s['total_votes'] > 0:
                avg_mp_votes = s['total_cast_votes'] / s['total_votes']
                print(f"   Average MPs per vote: {avg_mp_votes:.1f}")

        # Test 2: Most active voters
        print("\n2. Most Active Voters (by vote count)")
        print("-" * 40)
        active_voters = neo4j.run_query("""
            MATCH (mp:MP)-[cv:CAST_VOTE]->(v:Vote)
            WITH mp, count(cv) as vote_count
            ORDER BY vote_count DESC
            LIMIT 10
            RETURN
                mp.name as mp_name,
                mp.party as party,
                vote_count
        """)

        for av in active_voters:
            party = av['party'] or 'Independent'
            print(f"   {av['mp_name']:30} ({party:15}) - {av['vote_count']:,} votes")

        # Test 3: Party voting cohesion
        print("\n3. Party Voting Cohesion (dissent rates)")
        print("-" * 40)
        dissent = neo4j.run_query("""
            MATCH (mp:MP)-[cv:CAST_VOTE]->(v:Vote)
            WHERE mp.party IS NOT NULL
            WITH mp.party as party,
                 count(cv) as total_votes,
                 sum(CASE WHEN cv.dissent = true THEN 1 ELSE 0 END) as dissenting_votes
            WHERE total_votes > 100
            RETURN
                party,
                total_votes,
                dissenting_votes,
                (dissenting_votes * 100.0 / total_votes) as dissent_rate
            ORDER BY dissent_rate DESC
        """)

        for d in dissent:
            print(f"   {d['party']:20} - {d['dissent_rate']:5.2f}% dissent ({d['dissenting_votes']:,}/{d['total_votes']:,})")

        # Test 4: MPs with most dissenting votes
        print("\n4. Most Independent MPs (highest dissent rates)")
        print("-" * 40)
        dissenters = neo4j.run_query("""
            MATCH (mp:MP)-[cv:CAST_VOTE]->(v:Vote)
            WITH mp,
                 count(cv) as total_votes,
                 sum(CASE WHEN cv.dissent = true THEN 1 ELSE 0 END) as dissenting_votes
            WHERE total_votes > 50
            RETURN
                mp.name as mp_name,
                mp.party as party,
                dissenting_votes,
                total_votes,
                (dissenting_votes * 100.0 / total_votes) as dissent_rate
            ORDER BY dissent_rate DESC
            LIMIT 10
        """)

        for ds in dissenters:
            party = ds['party'] or 'Independent'
            print(f"   {ds['mp_name']:30} ({party:15}) - {ds['dissent_rate']:5.2f}% ({ds['dissenting_votes']}/{ds['total_votes']})")

        # Test 5: Recent voting patterns
        print("\n5. Recent Vote Distribution (last 30 days)")
        print("-" * 40)
        recent = neo4j.run_query("""
            MATCH (v:Vote)
            WHERE v.date >= date() - duration('P30D')
            OPTIONAL MATCH (mp:MP)-[cv:CAST_VOTE]->(v)
            RETURN
                v.date as vote_date,
                v.description as description,
                count(cv) as mp_votes,
                sum(CASE WHEN cv.position = 'Y' THEN 1 ELSE 0 END) as yea_votes,
                sum(CASE WHEN cv.position = 'N' THEN 1 ELSE 0 END) as nay_votes,
                sum(CASE WHEN cv.position = 'P' THEN 1 ELSE 0 END) as paired_votes
            ORDER BY v.date DESC
            LIMIT 5
        """)

        for r in recent:
            desc = (r['description'] or 'No description')[:50]
            print(f"\n   Date: {r['vote_date']}")
            print(f"   Desc: {desc}")
            print(f"   Result: {r['yea_votes']} Yea, {r['nay_votes']} Nay, {r['paired_votes']} Paired")

        # Test 6: Cross-reference with Terms
        print("\n6. Historical Career Analysis (MPs with multiple terms)")
        print("-" * 40)
        career = neo4j.run_query("""
            MATCH (mp:MP)-[:SERVED_TERM]->(t:Term)
            WITH mp, count(t) as term_count
            WHERE term_count > 3
            OPTIONAL MATCH (mp)-[cv:CAST_VOTE]->()
            WITH mp, term_count, count(cv) as vote_count
            ORDER BY term_count DESC
            LIMIT 10
            RETURN
                mp.name as mp_name,
                mp.party as party,
                term_count,
                vote_count
        """)

        for c in career:
            party = c['party'] or 'Independent'
            print(f"   {c['mp_name']:30} ({party:15}) - {c['term_count']} terms, {c['vote_count']:,} votes")

        # Test 7: Terms and riding representation
        print("\n7. Riding Representation Over Time")
        print("-" * 40)
        riding = neo4j.run_query("""
            MATCH (mp:MP)-[:SERVED_TERM]->(t:Term)-[:REPRESENTS]->(r:Riding)
            WITH r, count(t) as term_count, collect(DISTINCT mp.name) as mps
            ORDER BY term_count DESC
            LIMIT 10
            RETURN
                r.name as riding_name,
                term_count,
                size(mps) as unique_mps,
                mps[0..3] as sample_mps
        """)

        for rid in riding:
            sample = ', '.join(rid['sample_mps'][:3])
            if rid['unique_mps'] > 3:
                sample += f" (+ {rid['unique_mps'] - 3} more)"
            print(f"   {rid['riding_name']:40} - {rid['term_count']} terms, {rid['unique_mps']} MPs")
            print(f"      Sample MPs: {sample}")

        # Test 8: Vote position distribution
        print("\n8. Vote Position Distribution")
        print("-" * 40)
        positions = neo4j.run_query("""
            MATCH (mp:MP)-[cv:CAST_VOTE]->(v:Vote)
            WITH cv.position as position, count(*) as count
            WITH collect({position: position, count: count}) as position_data, sum(count) as total
            UNWIND position_data as pd
            RETURN
                pd.position as position,
                pd.count as count,
                (pd.count * 100.0 / total) as percentage
            ORDER BY pd.count DESC
        """)

        for p in positions:
            position_label = {
                'Y': 'Yea',
                'N': 'Nay',
                'P': 'Paired',
                None: 'Unknown'
            }.get(p['position'], p['position'])
            print(f"   {position_label:10} - {p['count']:,} votes ({p['percentage']:.1f}%)")

        # Test 9: Data quality check
        print("\n9. Data Quality Verification")
        print("-" * 40)
        quality = neo4j.run_query("""
            MATCH (mp:MP)
            OPTIONAL MATCH (mp)-[:SERVED_TERM]->(t:Term)
            OPTIONAL MATCH (mp)-[cv:CAST_VOTE]->()
            RETURN
                count(mp) as total_mps,
                count(t) as total_terms,
                count(cv) as total_votes,
                count(DISTINCT CASE WHEN exists((mp)-[:SERVED_TERM]->()) THEN mp END) as mps_with_terms,
                count(DISTINCT CASE WHEN exists((mp)-[:CAST_VOTE]->()) THEN mp END) as mps_with_votes,
                count(DISTINCT CASE WHEN mp.slug IS NULL OR mp.slug = '' THEN mp END) as mps_without_slug
        """)

        if quality:
            q = quality[0]
            print(f"   Total MPs: {q['total_mps']:,}")
            print(f"   MPs with terms: {q['mps_with_terms']:,} ({q['mps_with_terms']*100/q['total_mps']:.1f}%)")
            print(f"   MPs with votes: {q['mps_with_votes']:,} ({q['mps_with_votes']*100/q['total_mps']:.1f}%)")
            print(f"   Total terms: {q['total_terms']:,}")
            print(f"   Total votes: {q['total_votes']:,}")
            print(f"   MPs without slug: {q['mps_without_slug']:,}")

        # Test 10: Sample comprehensive MP profile
        print("\n10. Sample MP Comprehensive Profile")
        print("-" * 40)
        sample_mp = neo4j.run_query("""
            MATCH (mp:MP)
            WHERE exists((mp)-[:CAST_VOTE]->()) AND exists((mp)-[:SERVED_TERM]->())
            WITH mp
            ORDER BY rand()
            LIMIT 1

            OPTIONAL MATCH (mp)-[:SERVED_TERM]->(t:Term)
            OPTIONAL MATCH (mp)-[cv:CAST_VOTE]->()

            RETURN
                mp.name as name,
                mp.party as party,
                mp.slug as slug,
                count(DISTINCT t) as term_count,
                count(cv) as vote_count,
                sum(CASE WHEN cv.dissent = true THEN 1 ELSE 0 END) as dissent_count
        """)

        if sample_mp:
            s = sample_mp[0]
            print(f"   Name: {s['name']}")
            print(f"   Party: {s['party']}")
            print(f"   Slug: {s['slug']}")
            print(f"   Parliamentary Terms: {s['term_count']}")
            print(f"   Total Votes Cast: {s['vote_count']:,}")
            print(f"   Dissenting Votes: {s['dissent_count']} ({s['dissent_count']*100/s['vote_count']:.1f}%)")

    finally:
        neo4j.close()

    print("\n" + "=" * 80)
    print(f"✅ ANALYSIS COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == "__main__":
    main()
