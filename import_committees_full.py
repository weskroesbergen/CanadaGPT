#!/usr/bin/env python3
"""
Full Committee Data Migration from PostgreSQL to Neo4j

Complete bulk load of all committee data:
- All 124 committees + their full relationship graph
- All related meetings, activities, reports
- All relationships between entities

This is the production migration script.
"""

import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import psycopg2
from neo4j import GraphDatabase
from typing import List, Dict, Any
import time

# Load environment
load_dotenv(Path.home() / "FedMCP/packages/data-pipeline/.env")

# Database connections
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

PG_CONN_STRING = "dbname=openparliament"


class CommitteeMigration:
    """Handles migration of committee data from PostgreSQL to Neo4j"""

    def __init__(self):
        self.pg_conn = psycopg2.connect(PG_CONN_STRING)
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        self.stats = {
            'committees': 0,
            'committee_instances': 0,
            'meetings': 0,
            'activities': 0,
            'activity_instances': 0,
            'reports': 0,
            'relationships': 0,
            'errors': []
        }

    def close(self):
        """Close database connections"""
        self.pg_conn.close()
        self.neo4j_driver.close()

    def create_schema(self):
        """Create Neo4j constraints and indexes"""
        print("\n" + "=" * 80)
        print("CREATING NEO4J SCHEMA")
        print("=" * 80)

        schema_queries = [
            # Committee
            "CREATE CONSTRAINT committee_id IF NOT EXISTS FOR (c:Committee) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT committee_slug IF NOT EXISTS FOR (c:Committee) REQUIRE c.slug IS UNIQUE",
            "CREATE INDEX committee_name IF NOT EXISTS FOR (c:Committee) ON (c.name_en)",

            # CommitteeInstance
            "CREATE CONSTRAINT committee_instance_id IF NOT EXISTS FOR (ci:CommitteeInstance) REQUIRE ci.id IS UNIQUE",
            "CREATE INDEX committee_instance_session IF NOT EXISTS FOR (ci:CommitteeInstance) ON (ci.session_id)",

            # Meeting
            "CREATE CONSTRAINT meeting_id IF NOT EXISTS FOR (m:Meeting) REQUIRE m.id IS UNIQUE",
            "CREATE INDEX meeting_date IF NOT EXISTS FOR (m:Meeting) ON (m.date)",
            "CREATE INDEX meeting_session IF NOT EXISTS FOR (m:Meeting) ON (m.session_id)",

            # Activity
            "CREATE CONSTRAINT activity_id IF NOT EXISTS FOR (a:Activity) REQUIRE a.id IS UNIQUE",

            # ActivityInstance
            "CREATE CONSTRAINT activity_instance_id IF NOT EXISTS FOR (ai:ActivityInstance) REQUIRE ai.id IS UNIQUE",

            # Report
            "CREATE CONSTRAINT report_id IF NOT EXISTS FOR (r:Report) REQUIRE r.id IS UNIQUE",
            "CREATE INDEX report_session IF NOT EXISTS FOR (r:Report) ON (r.session_id)",
        ]

        with self.neo4j_driver.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                    constraint_name = query.split()[2] if "CONSTRAINT" in query else query.split()[2]
                    print(f"   ✓ Created: {constraint_name}")
                except Exception as e:
                    print(f"   ⚠ Warning: {str(e)}")

        print("\n✅ Schema creation complete")

    def fetch_committees(self) -> List[Dict[str, Any]]:
        """Fetch all committees from PostgreSQL"""
        print(f"\n📊 Fetching all committees...")

        query = """
            SELECT id, slug, name_en, name_fr, short_name_en, short_name_fr,
                   parent_id, joint, display
            FROM committees_committee
            WHERE display = true
            ORDER BY id
        """

        with self.pg_conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            committees = [dict(zip(columns, row)) for row in cur.fetchall()]

        print(f"   Found {len(committees)} committees")
        for c in committees[:5]:
            print(f"   - {c['name_en'][:60]}")
        if len(committees) > 5:
            print(f"   ... and {len(committees) - 5} more")

        return committees

    def fetch_committee_instances(self, committee_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch committee instances for given committee IDs"""
        print("\n📊 Fetching committee instances...")

        query = """
            SELECT id, session_id, committee_id, acronym
            FROM committees_committeeinsession
            WHERE committee_id = ANY(%s)
        """

        with self.pg_conn.cursor() as cur:
            cur.execute(query, (committee_ids,))
            columns = [desc[0] for desc in cur.description]
            instances = [dict(zip(columns, row)) for row in cur.fetchall()]

        print(f"   Found {len(instances)} committee instances across sessions")
        return instances

    def fetch_meetings(self, committee_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch meetings for given committee IDs"""
        print("\n📊 Fetching meetings...")

        query = """
            SELECT id, date, start_time, end_time, committee_id, number,
                   session_id, evidence_id, in_camera, travel, webcast, televised
            FROM committees_committeemeeting
            WHERE committee_id = ANY(%s)
            ORDER BY date DESC
        """

        with self.pg_conn.cursor() as cur:
            cur.execute(query, (committee_ids,))
            columns = [desc[0] for desc in cur.description]
            meetings = [dict(zip(columns, row)) for row in cur.fetchall()]

        print(f"   Found {len(meetings)} meetings")
        return meetings

    def fetch_activities(self, committee_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch activities for given committee IDs"""
        print("\n📊 Fetching activities...")

        query = """
            SELECT id, committee_id, name_en, name_fr, study
            FROM committees_committeeactivity
            WHERE committee_id = ANY(%s)
        """

        with self.pg_conn.cursor() as cur:
            cur.execute(query, (committee_ids,))
            columns = [desc[0] for desc in cur.description]
            activities = [dict(zip(columns, row)) for row in cur.fetchall()]

        print(f"   Found {len(activities)} activities")
        return activities

    def fetch_activity_instances(self, activity_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch activity instances for given activity IDs"""
        print("\n📊 Fetching activity instances...")

        query = """
            SELECT id, session_id, activity_id
            FROM committees_committeeactivityinsession
            WHERE activity_id = ANY(%s)
        """

        with self.pg_conn.cursor() as cur:
            cur.execute(query, (activity_ids,))
            columns = [desc[0] for desc in cur.description]
            instances = [dict(zip(columns, row)) for row in cur.fetchall()]

        print(f"   Found {len(instances)} activity instances")
        return instances

    def fetch_meeting_activities(self, meeting_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch meeting-activity links"""
        print("\n📊 Fetching meeting-activity links...")

        query = """
            SELECT committeemeeting_id, committeeactivity_id
            FROM committees_committeemeeting_activities
            WHERE committeemeeting_id = ANY(%s)
        """

        with self.pg_conn.cursor() as cur:
            cur.execute(query, (meeting_ids,))
            columns = [desc[0] for desc in cur.description]
            links = [dict(zip(columns, row)) for row in cur.fetchall()]

        print(f"   Found {len(links)} meeting-activity links")
        return links

    def fetch_reports(self, committee_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch reports for given committee IDs"""
        print("\n📊 Fetching reports...")

        query = """
            SELECT id, committee_id, session_id, number,
                   government_response, presented_date, parent_id
            FROM committees_committeereport
            WHERE committee_id = ANY(%s)
        """

        with self.pg_conn.cursor() as cur:
            cur.execute(query, (committee_ids,))
            columns = [desc[0] for desc in cur.description]
            reports = [dict(zip(columns, row)) for row in cur.fetchall()]

        print(f"   Found {len(reports)} reports")
        return reports

    def load_committees(self, committees: List[Dict[str, Any]]):
        """Load committees into Neo4j"""
        print("\n📥 Loading committees into Neo4j...")

        query = """
        UNWIND $batch as row
        MERGE (c:Committee {id: row.id})
        SET c.slug = row.slug,
            c.name_en = row.name_en,
            c.name_fr = row.name_fr,
            c.short_name_en = row.short_name_en,
            c.short_name_fr = row.short_name_fr,
            c.joint = row.joint,
            c.display = row.display,
            c.parent_id = row.parent_id
        RETURN count(c) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(query, batch=committees)
            count = result.single()['created']
            self.stats['committees'] = count
            print(f"   ✓ Loaded {count} committees")

        # Create parent-child relationships
        parent_query = """
        MATCH (child:Committee)
        WHERE child.parent_id IS NOT NULL
        MATCH (parent:Committee {id: child.parent_id})
        MERGE (parent)-[:PARENT_OF]->(child)
        RETURN count(*) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(parent_query)
            count = result.single()['created']
            if count > 0:
                print(f"   ✓ Created {count} parent-child relationships")
            self.stats['relationships'] += count

    def load_committee_instances(self, instances: List[Dict[str, Any]]):
        """Load committee instances into Neo4j"""
        print("\n📥 Loading committee instances...")

        query = """
        UNWIND $batch as row
        MERGE (ci:CommitteeInstance {id: row.id})
        SET ci.session_id = row.session_id,
            ci.acronym = row.acronym

        WITH ci, row
        MATCH (c:Committee {id: row.committee_id})
        MERGE (c)-[:HAS_INSTANCE]->(ci)

        RETURN count(ci) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(query, batch=instances)
            count = result.single()['created']
            self.stats['committee_instances'] = count
            self.stats['relationships'] += count  # HAS_INSTANCE relationships
            print(f"   ✓ Loaded {count} committee instances with relationships")

    def load_meetings(self, meetings: List[Dict[str, Any]]):
        """Load meetings into Neo4j"""
        print("\n📥 Loading meetings...")

        # Convert dates and times to strings for Neo4j
        for m in meetings:
            if m['date']:
                m['date'] = str(m['date'])
            if m['start_time']:
                m['start_time'] = str(m['start_time'])
            if m['end_time']:
                m['end_time'] = str(m['end_time']) if m['end_time'] else None

        query = """
        UNWIND $batch as row
        MERGE (m:Meeting {id: row.id})
        SET m.date = row.date,
            m.start_time = row.start_time,
            m.end_time = row.end_time,
            m.number = row.number,
            m.session_id = row.session_id,
            m.in_camera = row.in_camera,
            m.travel = row.travel,
            m.webcast = row.webcast,
            m.televised = row.televised,
            m.evidence_id = row.evidence_id

        WITH m, row
        MATCH (c:Committee {id: row.committee_id})-[:HAS_INSTANCE]->(ci:CommitteeInstance {session_id: row.session_id})
        MERGE (ci)-[:HELD_MEETING]->(m)

        RETURN count(m) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(query, batch=meetings)
            count = result.single()['created']
            self.stats['meetings'] = count
            self.stats['relationships'] += count  # HELD_MEETING relationships
            print(f"   ✓ Loaded {count} meetings with relationships")

    def load_activities(self, activities: List[Dict[str, Any]]):
        """Load activities into Neo4j"""
        print("\n📥 Loading activities...")

        query = """
        UNWIND $batch as row
        MERGE (a:Activity {id: row.id})
        SET a.name_en = row.name_en,
            a.name_fr = row.name_fr,
            a.study = row.study

        WITH a, row
        MATCH (c:Committee {id: row.committee_id})
        MERGE (c)-[:HAS_ACTIVITY]->(a)

        RETURN count(a) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(query, batch=activities)
            count = result.single()['created']
            self.stats['activities'] = count
            self.stats['relationships'] += count  # HAS_ACTIVITY relationships
            print(f"   ✓ Loaded {count} activities with relationships")

    def load_activity_instances(self, instances: List[Dict[str, Any]]):
        """Load activity instances into Neo4j"""
        print("\n📥 Loading activity instances...")

        query = """
        UNWIND $batch as row
        MERGE (ai:ActivityInstance {id: row.id})
        SET ai.session_id = row.session_id

        WITH ai, row
        MATCH (a:Activity {id: row.activity_id})
        MERGE (a)-[:IN_SESSION]->(ai)

        RETURN count(ai) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(query, batch=instances)
            count = result.single()['created']
            self.stats['activity_instances'] = count
            self.stats['relationships'] += count  # IN_SESSION relationships
            print(f"   ✓ Loaded {count} activity instances with relationships")

    def load_meeting_activities(self, links: List[Dict[str, Any]]):
        """Load meeting-activity links into Neo4j"""
        print("\n📥 Loading meeting-activity links...")

        query = """
        UNWIND $batch as row
        MATCH (m:Meeting {id: row.committeemeeting_id})
        MATCH (a:Activity {id: row.committeeactivity_id})
        MERGE (m)-[:DISCUSSED]->(a)
        RETURN count(*) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(query, batch=links)
            count = result.single()['created']
            self.stats['relationships'] += count
            print(f"   ✓ Created {count} meeting-activity relationships")

    def load_reports(self, reports: List[Dict[str, Any]]):
        """Load reports into Neo4j"""
        print("\n📥 Loading reports...")

        # Convert dates to strings
        for r in reports:
            if r['presented_date']:
                r['presented_date'] = str(r['presented_date'])

        query = """
        UNWIND $batch as row
        MERGE (r:Report {id: row.id})
        SET r.session_id = row.session_id,
            r.number = row.number,
            r.government_response = row.government_response,
            r.presented_date = row.presented_date

        WITH r, row
        MATCH (c:Committee {id: row.committee_id})
        MERGE (c)-[:PUBLISHED_REPORT]->(r)

        RETURN count(r) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(query, batch=reports)
            count = result.single()['created']
            self.stats['reports'] = count
            self.stats['relationships'] += count  # PUBLISHED_REPORT relationships
            print(f"   ✓ Loaded {count} reports with relationships")

        # Create parent report relationships
        parent_query = """
        MATCH (child:Report)
        WHERE child.parent_id IS NOT NULL
        MATCH (parent:Report {id: child.parent_id})
        MERGE (child)-[:RESPONSE_TO]->(parent)
        RETURN count(*) as created
        """

        with self.neo4j_driver.session() as session:
            result = session.run(parent_query)
            count = result.single()['created']
            if count > 0:
                print(f"   ✓ Created {count} report response relationships")
                self.stats['relationships'] += count

    def validate_migration(self):
        """Validate the migrated data"""
        print("\n" + "=" * 80)
        print("VALIDATION")
        print("=" * 80)

        queries = {
            "Committees": "MATCH (c:Committee) RETURN count(c) as count",
            "Committee Instances": "MATCH (ci:CommitteeInstance) RETURN count(ci) as count",
            "Meetings": "MATCH (m:Meeting) RETURN count(m) as count",
            "Activities": "MATCH (a:Activity) RETURN count(a) as count",
            "Activity Instances": "MATCH (ai:ActivityInstance) RETURN count(ai) as count",
            "Reports": "MATCH (r:Report) RETURN count(r) as count",
            "Total Relationships": "MATCH ()-[r]->() RETURN count(r) as count",
        }

        with self.neo4j_driver.session() as session:
            for label, query in queries.items():
                result = session.run(query)
                count = result.single()['count']
                print(f"   {label:25} {count:7,}")

        # Sample queries
        print("\n📊 Sample Query Results:")

        sample_queries = [
            ("Committees with most meetings", """
                MATCH (c:Committee)-[:HAS_INSTANCE]->(ci:CommitteeInstance)-[:HELD_MEETING]->(m:Meeting)
                RETURN c.short_name_en as committee, count(m) as meetings
                ORDER BY meetings DESC
                LIMIT 5
            """),
            ("Most active study topics", """
                MATCH (a:Activity)<-[:DISCUSSED]-(m:Meeting)
                WHERE a.study = true
                RETURN a.name_en as topic, count(m) as meetings
                ORDER BY meetings DESC
                LIMIT 5
            """),
        ]

        with self.neo4j_driver.session() as session:
            for title, query in sample_queries:
                print(f"\n   {title}:")
                result = session.run(query)
                for record in result:
                    print(f"      - {record[0]}: {record[1]:,}")

    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)

        print("\n✅ Successfully migrated:")
        print(f"   Committees:           {self.stats['committees']:7,}")
        print(f"   Committee Instances:  {self.stats['committee_instances']:7,}")
        print(f"   Meetings:             {self.stats['meetings']:7,}")
        print(f"   Activities:           {self.stats['activities']:7,}")
        print(f"   Activity Instances:   {self.stats['activity_instances']:7,}")
        print(f"   Reports:              {self.stats['reports']:7,}")
        print(f"   Total Relationships:  {self.stats['relationships']:7,}")

        if self.stats['errors']:
            print(f"\n⚠ Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                print(f"   - {error}")

    def run(self):
        """Execute the full migration"""
        print("=" * 80)
        print("COMMITTEE DATA FULL MIGRATION")
        print("PostgreSQL → Neo4j")
        print("=" * 80)

        start_time = time.time()

        try:
            # Step 1: Create schema
            self.create_schema()

            # Step 2: Extract data
            committees = self.fetch_committees()
            committee_ids = [c['id'] for c in committees]

            instances = self.fetch_committee_instances(committee_ids)
            meetings = self.fetch_meetings(committee_ids)
            activities = self.fetch_activities(committee_ids)

            activity_ids = [a['id'] for a in activities] if activities else []
            activity_instances = self.fetch_activity_instances(activity_ids) if activity_ids else []

            meeting_ids = [m['id'] for m in meetings] if meetings else []
            meeting_activities = self.fetch_meeting_activities(meeting_ids) if meeting_ids else []

            reports = self.fetch_reports(committee_ids)

            # Step 3: Load data
            print("\n" + "=" * 80)
            print("LOADING DATA INTO NEO4J")
            print("=" * 80)

            self.load_committees(committees)
            if instances:
                self.load_committee_instances(instances)
            if activities:
                self.load_activities(activities)
            if activity_instances:
                self.load_activity_instances(activity_instances)
            if meetings:
                self.load_meetings(meetings)
            if meeting_activities:
                self.load_meeting_activities(meeting_activities)
            if reports:
                self.load_reports(reports)

            # Step 4: Validate
            self.validate_migration()

            # Step 5: Summary
            elapsed = time.time() - start_time
            self.print_summary()

            print(f"\n⏱  Total time: {elapsed:.2f} seconds")
            print("\n" + "=" * 80)
            print("✅ FULL MIGRATION COMPLETE")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            self.stats['errors'].append(str(e))
        finally:
            self.close()


if __name__ == "__main__":
    migration = CommitteeMigration()
    migration.run()
