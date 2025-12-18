# MCP Servers Setup Guide for CanadaGPT

This guide explains how to install and configure Model Context Protocol (MCP) servers for the CanadaGPT project in Claude Code.

## Overview

MCP servers extend Claude Code's capabilities by providing specialized tools and context. We've selected servers optimized for this Next.js/GraphQL/Neo4j monorepo.

## Recommended MCP Servers

### 1. Next.js DevTools MCP (Vercel Official)
**Purpose**: AI-assisted Next.js development with runtime diagnostics
**Repository**: [vercel/next-devtools-mcp](https://github.com/vercel/next-devtools-mcp)

**Capabilities**:
- Access live build/runtime errors from Next.js 16+ dev server
- Query routes, component metadata, and server logs
- Automated Next.js 16 upgrades with codemods
- Cache Components setup and debugging
- Next.js documentation search
- Browser testing via Playwright

**Installation**: No installation needed, uses npx

**Configuration**:
```json
{
  "next-devtools": {
    "command": "npx",
    "args": ["-y", "next-devtools-mcp@latest"]
  }
}
```

**Usage**: Start your dev server (`pnpm dev:frontend`), then use the `init` tool to begin

---

### 2. GraphQL MCP
**Purpose**: Interact with GraphQL APIs through schema introspection and queries
**Repository**: [blurrah/mcp-graphql](https://github.com/blurrah/mcp-graphql)

**Capabilities**:
- Introspect GraphQL schema
- Execute queries against endpoints
- Support for custom headers
- Mutations disabled by default (security)

**Installation**: No installation needed, uses npx

**Configuration**:
```json
{
  "graphql": {
    "command": "npx",
    "args": ["mcp-graphql"],
    "env": {
      "ENDPOINT": "http://localhost:4000/graphql",
      "ALLOW_MUTATIONS": "false"
    }
  }
}
```

**Tools**:
- `introspect-schema` - Retrieve GraphQL schema
- `query-graphql` - Execute queries

---

### 3. Neo4j MCP (Official)
**Purpose**: Interact with Neo4j graph database
**Repository**: [neo4j/mcp](https://github.com/neo4j/mcp)

**Capabilities**:
- Schema introspection (labels, relationships, properties)
- Read-only Cypher queries
- Write Cypher queries (development mode)
- Graph Data Science procedures

**Installation**:
```bash
# Download binary from https://github.com/neo4j/mcp/releases

# Mac/Linux:
chmod +x neo4j-mcp
sudo mv neo4j-mcp /usr/local/bin/

# Windows:
# Move neo4j-mcp.exe to C:\Windows\System32

# Verify:
neo4j-mcp -v
```

**Configuration**:
```json
{
  "neo4j": {
    "command": "neo4j-mcp",
    "env": {
      "NEO4J_URI": "bolt://localhost:7687",
      "NEO4J_USERNAME": "neo4j",
      "NEO4J_PASSWORD": "your_password",
      "NEO4J_DATABASE": "neo4j",
      "NEO4J_READ_ONLY": "false"
    }
  }
}
```

**Tools**:
- `get-schema` - Introspect database schema
- `read-cypher` - Execute read-only queries
- `write-cypher` - Execute all Cypher (use cautiously)
- `list-gds-procedures` - Graph Data Science procedures

**Production Configuration**:
```json
{
  "neo4j-production": {
    "command": "neo4j-mcp",
    "env": {
      "NEO4J_URI": "bolt://10.128.0.3:7687",
      "NEO4J_USERNAME": "neo4j",
      "NEO4J_PASSWORD": "canadagpt2024",
      "NEO4J_DATABASE": "neo4j",
      "NEO4J_READ_ONLY": "true"
    }
  }
}
```

---

### 4. Git MCP (Official Anthropic)
**Purpose**: Git repository interaction and automation
**Repository**: [modelcontextprotocol/servers/git](https://github.com/modelcontextprotocol/servers/tree/main/src/git)

**Capabilities**:
- Check status, diff, log
- Create commits, branches
- Checkout, merge operations
- Stash management
- Tag operations

**Installation**: No installation needed, uses uvx

**Configuration**:
```json
{
  "git": {
    "command": "uvx",
    "args": ["mcp-server-git", "--repository", "/Users/matthewdufresne/CanadaGPT"]
  }
}
```

**Tools** (12+ operations):
- `git_status`, `git_diff_unstaged`, `git_diff_staged`
- `git_commit`, `git_log`, `git_checkout`
- `git_branch`, `git_merge`, `git_stash`
- And more...

---

### 5. Filesystem MCP (Official Anthropic)
**Purpose**: Secure file operations with access controls
**Repository**: [modelcontextprotocol/servers/filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)

**Capabilities**:
- Read/write files
- Directory creation, listing, deletion
- File movement and renaming
- Search with pattern matching
- File metadata retrieval
- Dynamic access control via MCP Roots

**Installation**: No installation needed, uses npx

**Configuration**:
```json
{
  "filesystem": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-filesystem",
      "/Users/matthewdufresne/CanadaGPT"
    ]
  }
}
```

**Tools**:
- `read_text_file` - Read file contents
- `edit_file` - Make selective edits with dry-run
- `write_file` - Create/overwrite files
- `search_files` - Recursive pattern matching
- `directory_tree` - JSON structure output
- `list_allowed_directories` - View accessible paths

---

## Installation Steps

### Step 1: Download Neo4j MCP Binary

```bash
# Go to https://github.com/neo4j/mcp/releases
# Download the binary for your platform

# Mac/Linux:
chmod +x neo4j-mcp
sudo mv neo4j-mcp /usr/local/bin/

# Verify:
neo4j-mcp -v
```

### Step 2: Create Claude Code MCP Configuration

Create or update `~/.claude/config.json`:

```bash
mkdir -p ~/.claude
cat > ~/.claude/config.json << 'EOF'
{
  "mcpServers": {
    "next-devtools": {
      "command": "npx",
      "args": ["-y", "next-devtools-mcp@latest"]
    },
    "graphql": {
      "command": "npx",
      "args": ["mcp-graphql"],
      "env": {
        "ENDPOINT": "http://localhost:4000/graphql",
        "ALLOW_MUTATIONS": "false"
      }
    },
    "neo4j-local": {
      "command": "neo4j-mcp",
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "canadagpt2024",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_READ_ONLY": "false"
      }
    },
    "neo4j-production": {
      "command": "neo4j-mcp",
      "env": {
        "NEO4J_URI": "bolt://10.128.0.3:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "canadagpt2024",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_READ_ONLY": "true"
      }
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "/Users/matthewdufresne/CanadaGPT"]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/matthewdufresne/CanadaGPT"
      ]
    }
  }
}
EOF
```

### Step 3: Restart Claude Code

```bash
# If Claude Code is running, restart it to load the new configuration
# The MCP servers will be available in your next session
```

### Step 4: Verify Installation

In Claude Code, you should now have access to these new MCP tools. Try:

- `next-devtools` tools after starting dev server
- `graphql` introspection and queries
- `neo4j` schema inspection and Cypher queries
- `git` operations on your repository
- `filesystem` operations

## Usage Examples

### Next.js Development

```
# Start dev server first
pnpm dev:frontend

# Then ask Claude:
"Use the next-devtools init tool to connect to my dev server"
"Show me all build errors in my Next.js app"
"What routes are currently registered?"
```

### GraphQL Operations

```
"Use the graphql introspect-schema tool to show me the schema"
"Query all MPs from the GraphQL API"
"Show me the Bill type definition"
```

### Neo4j Queries

```
"Use neo4j get-schema to show the database structure"
"Use neo4j read-cypher to find all debates from November 2025"
"Show me MPs who spoke in the latest Hansard debate"
```

### Git Operations

```
"Use git_status to show uncommitted changes"
"Create a new branch called feature/mcp-servers"
"Show me the last 5 commits"
```

### Filesystem Operations

```
"Read the contents of packages/frontend/src/app/page.tsx"
"Search for files containing 'GraphQL' in packages/frontend"
"Show me the directory tree of packages/graph-api/src"
```

## Troubleshooting

### Neo4j MCP Connection Issues

**Problem**: `neo4j-mcp: command not found`

**Solution**:
```bash
# Verify binary is in PATH
which neo4j-mcp

# If not found, add to PATH:
export PATH="/usr/local/bin:$PATH"

# Or move binary:
sudo mv neo4j-mcp /usr/local/bin/
```

**Problem**: Connection refused to Neo4j

**Solution**:
```bash
# Verify Neo4j is running:
docker-compose ps neo4j

# Or check production via SSH tunnel:
./scripts/dev-tunnel.sh
```

### GraphQL MCP Issues

**Problem**: Cannot connect to GraphQL endpoint

**Solution**:
```bash
# Start the Graph API server:
pnpm dev:api

# Verify it's running:
curl http://localhost:4000/graphql
```

### Next.js DevTools Issues

**Problem**: "No dev server found"

**Solution**:
```bash
# Start frontend dev server:
pnpm dev:frontend

# Ensure Next.js 16+ for full features:
pnpm --filter @canadagpt/frontend upgrade next@latest
```

## Security Notes

1. **Neo4j Production**: Configured with `READ_ONLY: true` to prevent accidental writes
2. **GraphQL Mutations**: Disabled by default (`ALLOW_MUTATIONS: false`)
3. **Filesystem Access**: Limited to the CanadaGPT project directory
4. **Git Operations**: Scoped to the CanadaGPT repository

## Additional Resources

- [Next.js DevTools MCP](https://github.com/vercel/next-devtools-mcp)
- [GraphQL MCP](https://github.com/blurrah/mcp-graphql)
- [Neo4j MCP](https://github.com/neo4j/mcp)
- [Official Anthropic MCP Servers](https://github.com/modelcontextprotocol/servers)
- [MCP Registry](https://registry.modelcontextprotocol.io/)
- [Apollo MCP Server](https://www.apollographql.com/docs/apollo-mcp-server) (alternative GraphQL option)

## Already Installed MCP Servers

Your Claude Code setup already includes:
- `fedmcp` - Canadian parliamentary and legal data
- `canadagpt-neo4j` - Neo4j graph database management
- `github` - GitHub integration
- `memory` - Knowledge graph
- `postgres-supabase` - PostgreSQL queries
- `sequential-thinking` - Problem-solving

## Sources

- [Next.js MCP Server Guide](https://nextjs.org/docs/app/guides/mcp)
- [Vercel Next.js DevTools MCP](https://github.com/vercel/next-devtools-mcp)
- [Apollo GraphQL MCP Launch](https://www.apollographql.com/blog/the-future-of-mcp-is-graphql)
- [Neo4j MCP Developer Guide](https://neo4j.com/developer/genai-ecosystem/model-context-protocol-mcp/)
- [Official Neo4j MCP Server](https://github.com/neo4j/mcp)
- [Official Anthropic MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)
