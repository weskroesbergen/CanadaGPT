# CanadaGPT Neo4j MCP

Model Context Protocol (MCP) server for managing CanadaGPT's Neo4j graph database.

## Overview

This MCP server provides 8 tools for Neo4j database management, complementing FedMCP's data access capabilities with graph database operations:

- **execute_cypher_query** - Run Cypher queries with parameter support
- **get_cypher_template** - Retrieve pre-built query templates
- **validate_schema** - Compare Neo4j schema against GraphQL definitions
- **backfill_spoke_at** - Create SPOKE_AT relationships
- **diagnose_mp_linking** - Analyze MP name matching success rates
- **get_database_stats** - Comprehensive database statistics
- **check_data_freshness** - Verify ingestion pipeline freshness
- **analyze_graph_patterns** - Detect anomalies and patterns

## Installation

```bash
cd /Users/matthewdufresne/CanadaGPT/packages/canadagpt-neo4j-mcp
pip install -e .
```

## Configuration

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "canadagpt-neo4j": {
      "command": "python3",
      "args": ["-m", "canadagpt_neo4j.server"],
      "cwd": "/Users/matthewdufresne/CanadaGPT/packages/canadagpt-neo4j-mcp",
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "canadagpt2024",
        "NEO4J_DATABASE": "neo4j",
        "GRAPHQL_SCHEMA_PATH": "/Users/matthewdufresne/CanadaGPT/packages/graph-api/src/schema.ts"
      }
    }
  }
}
```

## Usage Examples

### Get Database Statistics
```
"Get Neo4j database statistics"
```

### Diagnose MP Linking
```
"What's the MP linking rate for debates from Nov 20-27?"
```

### Validate Schema
```
"Validate the Neo4j schema against GraphQL definitions"
```

### Execute Custom Query
```
"Run a Cypher query: MATCH (mp:MP {name: 'Pierre Poilievre'})-[:SPOKE_AT]->(d:Document) RETURN count(d)"
```

## Development

```bash
# Install in development mode
pip install -e .

# Test locally
python -m canadagpt_neo4j.server
```

## License

See root CanadaGPT project license.
