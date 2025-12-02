"""CanadaGPT Neo4j MCP Server - Graph database management tools."""

import os
import asyncio
import logging
import json
from typing import Any, Optional
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Neo4j driver
from neo4j import GraphDatabase

# Import our modules
from .queries import get_query_templates, format_query_result
from .schema import validate_schema_against_graphql
from .diagnostics import (
    diagnose_mp_linking,
    check_data_freshness,
    analyze_graph_patterns
)

# Initialize Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "canadagpt2024")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
GRAPHQL_SCHEMA_PATH = os.getenv("GRAPHQL_SCHEMA_PATH", "")

# Create Neo4j driver instance
try:
    neo4j_driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )
    logger.info(f"Connected to Neo4j at {NEO4J_URI}")
except Exception as e:
    logger.error(f"Failed to connect to Neo4j: {e}")
    neo4j_driver = None

# Create MCP server
app = Server(
    name="CanadaGPT Neo4j",
    version="1.0.0",
    instructions="Graph database management tools for CanadaGPT"
)

# Helper functions
async def run_sync(func, *args, **kwargs):
    """Run synchronous function in thread pool."""
    return await asyncio.to_thread(func, *args, **kwargs)


def execute_cypher(query: str, parameters: dict = None, allow_writes: bool = False) -> dict:
    """Execute Cypher query and return results."""
    if not neo4j_driver:
        return {"error": "Neo4j driver not initialized"}

    # Safety check for write operations
    query_upper = query.strip().upper()
    is_write_query = any(
        query_upper.startswith(keyword)
        for keyword in ["CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DROP"]
    )

    if is_write_query and not allow_writes:
        return {
            "error": "Write operations require allow_writes=true parameter",
            "query": query
        }

    try:
        with neo4j_driver.session(database=NEO4J_DATABASE) as session:
            start_time = datetime.now()
            result = session.run(query, parameters or {})
            records = [dict(record) for record in result]
            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "records": records,
                "row_count": len(records),
                "execution_time_seconds": execution_time,
                "query": query,
                "parameters": parameters or {}
            }
    except Exception as e:
        logger.error(f"Query error: {e}")
        return {
            "error": str(e),
            "query": query,
            "parameters": parameters or {}
        }


def backfill_spoke_at_relationships(
    date_from: str,
    date_to: str,
    dry_run: bool = True
) -> dict:
    """Create SPOKE_AT relationships from Statement and CommitteeTestimony nodes."""
    if not neo4j_driver:
        return {"error": "Neo4j driver not initialized"}

    try:
        with neo4j_driver.session(database=NEO4J_DATABASE) as session:
            # Hansard SPOKE_AT relationships
            hansard_query = """
            MATCH (mp:MP)<-[:MADE_BY]-(s:Statement)-[:PART_OF]->(d:Document)
            WHERE d.date >= $date_from AND d.date <= $date_to
            """

            if dry_run:
                count_query = hansard_query + " RETURN count(*) as count"
                result = session.run(count_query, {"date_from": date_from, "date_to": date_to})
                hansard_count = result.single()["count"]
            else:
                merge_query = hansard_query + """
                MERGE (mp)-[spoke:SPOKE_AT {
                    timestamp: s.time,
                    statement_id: s.id,
                    intervention_id: s.intervention_id,
                    person_db_id: s.person_db_id
                }]->(d)
                RETURN count(*) as count
                """
                result = session.run(merge_query, {"date_from": date_from, "date_to": date_to})
                hansard_count = result.single()["count"]

            # Committee SPOKE_AT relationships
            committee_query = """
            MATCH (mp:MP)<-[:TESTIFIED_BY]-(t:CommitteeTestimony)-[:GIVEN_IN]->(e:CommitteeEvidence)
            WHERE e.date >= $date_from AND e.date <= $date_to
            """

            if dry_run:
                count_query = committee_query + " RETURN count(*) as count"
                result = session.run(count_query, {"date_from": date_from, "date_to": date_to})
                committee_count = result.single()["count"]
            else:
                merge_query = committee_query + """
                MERGE (mp)-[spoke:SPOKE_AT {
                    testimony_id: t.id,
                    intervention_id: t.intervention_id,
                    person_db_id: t.person_db_id,
                    timestamp_hour: t.timestamp_hour,
                    timestamp_minute: t.timestamp_minute
                }]->(e)
                RETURN count(*) as count
                """
                result = session.run(merge_query, {"date_from": date_from, "date_to": date_to})
                committee_count = result.single()["count"]

            return {
                "dry_run": dry_run,
                "date_from": date_from,
                "date_to": date_to,
                "hansard_relationships": hansard_count,
                "committee_relationships": committee_count,
                "total_relationships": hansard_count + committee_count,
                "message": "Dry run - no changes made" if dry_run else "Relationships created successfully"
            }
    except Exception as e:
        logger.error(f"Backfill error: {e}")
        return {"error": str(e)}


def get_database_statistics() -> dict:
    """Get comprehensive database statistics."""
    if not neo4j_driver:
        return {"error": "Neo4j driver not initialized"}

    try:
        with neo4j_driver.session(database=NEO4J_DATABASE) as session:
            # Node counts
            node_labels = ["MP", "Document", "Statement", "Vote", "Bill", "Committee",
                          "CommitteeEvidence", "CommitteeTestimony", "Party", "Riding",
                          "LobbyRegistration", "LobbyCommunication"]
            node_counts = {}
            for label in node_labels:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                node_counts[label] = result.single()["count"]

            # Relationship counts
            rel_types = ["MADE_BY", "SPOKE_AT", "CAST_IN", "TESTIFIED_BY", "REPRESENTS",
                        "MEMBER_OF", "HELD_MEETING", "HAS_EVIDENCE"]
            relationship_counts = {}
            for rel_type in rel_types:
                result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                relationship_counts[rel_type] = result.single()["count"]

            # Storage info
            storage_query = """
            MATCH (n)
            OPTIONAL MATCH ()-[r]->()
            RETURN count(DISTINCT n) as nodes,
                   count(DISTINCT r) as relationships,
                   sum([k IN keys(n) | 1]) as properties
            """
            storage_result = session.run(storage_query).single()

            # Latest data dates
            latest_dates = {}
            date_queries = {
                "hansard": "MATCH (d:Document) RETURN max(d.date) as latest_date",
                "votes": "MATCH (v:Vote) RETURN max(v.date) as latest_date",
                "committee_evidence": "MATCH (e:CommitteeEvidence) RETURN max(e.date) as latest_date"
            }
            for key, query in date_queries.items():
                result = session.run(query).single()
                latest_dates[key] = result["latest_date"] if result and result["latest_date"] else "N/A"

            return {
                "node_counts": node_counts,
                "relationship_counts": relationship_counts,
                "storage_info": {
                    "nodes": storage_result["nodes"],
                    "relationships": storage_result["relationships"],
                    "properties": storage_result["properties"]
                },
                "latest_data_dates": latest_dates
            }
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        return {"error": str(e)}


# MCP Tool Handlers

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="execute_cypher_query",
            description="Execute a Cypher query against the Neo4j database. Returns results as JSON with row count and execution time. Write operations require allow_writes=true.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Cypher query to execute"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters (optional)",
                        "default": {}
                    },
                    "allow_writes": {
                        "type": "boolean",
                        "description": "Allow CREATE/MERGE/DELETE operations",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_cypher_template",
            description="Get a pre-built Cypher query template. Available templates: recent_debates, mp_speeches, spoke_at_stats, vote_analysis, committee_evidence, lobbying_by_bill, data_freshness, mp_linking_diagnostics",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_name": {
                        "type": "string",
                        "description": "Template name",
                        "enum": ["recent_debates", "mp_speeches", "spoke_at_stats", "vote_analysis",
                                "committee_evidence", "lobbying_by_bill", "data_freshness", "mp_linking_diagnostics"]
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Template parameters",
                        "default": {}
                    }
                },
                "required": ["template_name"]
            }
        ),
        Tool(
            name="validate_schema",
            description="Validate Neo4j graph schema against GraphQL schema definitions. Checks for missing node labels, relationship types, and orphaned nodes.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="backfill_spoke_at",
            description="Create SPOKE_AT relationships from Statement and CommitteeTestimony nodes for a date range. Use dry_run=true to preview changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD format)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD format)"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without creating relationships",
                        "default": True
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="diagnose_mp_linking",
            description="Analyze MP name matching success rates for a date range. Returns linking rate, unmatched speakers, and suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD format)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD format)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_database_stats",
            description="Get comprehensive database statistics including node counts, relationship counts, storage info, and latest data dates.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="check_data_freshness",
            description="Check data freshness against expected publication schedules. Flags stale data beyond thresholds.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="analyze_graph_patterns",
            description="Detect anomalies and patterns in the graph: debate volume gaps, MP activity dropoffs, committee spikes, lobbying correlations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date for analysis (YYYY-MM-DD format, optional)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date for analysis (YYYY-MM-DD format, optional)"
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "execute_cypher_query":
            query = arguments.get("query", "")
            parameters = arguments.get("parameters", {})
            allow_writes = arguments.get("allow_writes", False)

            result = await run_sync(execute_cypher, query, parameters, allow_writes)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "get_cypher_template":
            template_name = arguments.get("template_name", "")
            parameters = arguments.get("parameters", {})

            templates = get_query_templates()
            if template_name not in templates:
                return [TextContent(
                    type="text",
                    text=f"Template '{template_name}' not found. Available: {', '.join(templates.keys())}"
                )]

            template = templates[template_name]
            result = {
                "template_name": template_name,
                "description": template["description"],
                "query": template["query"],
                "parameters": template.get("parameters", {}),
                "provided_parameters": parameters
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "validate_schema":
            if not GRAPHQL_SCHEMA_PATH or not os.path.exists(GRAPHQL_SCHEMA_PATH):
                return [TextContent(
                    type="text",
                    text=f"GraphQL schema path not configured or not found: {GRAPHQL_SCHEMA_PATH}"
                )]

            result = await run_sync(validate_schema_against_graphql, neo4j_driver, GRAPHQL_SCHEMA_PATH, NEO4J_DATABASE)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "backfill_spoke_at":
            date_from = arguments.get("date_from", "")
            date_to = arguments.get("date_to", "")
            dry_run = arguments.get("dry_run", True)

            result = await run_sync(backfill_spoke_at_relationships, date_from, date_to, dry_run)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "diagnose_mp_linking":
            date_from = arguments.get("date_from", "")
            date_to = arguments.get("date_to", "")

            result = await run_sync(diagnose_mp_linking, neo4j_driver, date_from, date_to, NEO4J_DATABASE)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "get_database_stats":
            result = await run_sync(get_database_statistics)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "check_data_freshness":
            result = await run_sync(check_data_freshness, neo4j_driver, NEO4J_DATABASE)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "analyze_graph_patterns":
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")

            result = await run_sync(analyze_graph_patterns, neo4j_driver, date_from, date_to, NEO4J_DATABASE)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Tool call error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
