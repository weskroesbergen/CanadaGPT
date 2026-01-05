# Claude Code Configuration

This directory contains Claude Code skills and local project settings.

## Skills

Located in `.claude/skills/`, these custom commands enhance the development workflow:

- **`/deploy-production`** - Deploy Graph API and Frontend to Google Cloud Run with full pre-deployment checks and verification
- **`/deploy-ingestion`** - Deploy all data pipeline jobs (Hansard, MPs, Votes, Committees, Lobbying, Expenses)
- **`/check-data-freshness`** - Validate that production data is up-to-date and ingestion jobs are functioning

## Usage

In Claude Code, type `/deploy-production` (or other skill name) to invoke the skill. Skills provide guided workflows for complex tasks.

## Enabled MCP Servers

Configured in `~/Library/Application Support/Claude/claude_desktop_config.json`:

### Project-Specific MCPs
- **fedmcp** - Canadian parliamentary and legal data (40+ tools for debates, bills, MPs, lobbying, expenses, etc.)
- **canadagpt-neo4j** - Custom Neo4j MCP with CanadaGPT schema awareness
- **postgres-supabase** - Supabase PostgreSQL database access

### Development MCPs
- **gcp** - Google Cloud Platform management (Cloud Run, Cloud Scheduler, logging, etc.) ⭐ NEW
- **docker** - Docker container management (inspect, logs, exec) ⭐ NEW
- **github** - GitHub API integration
- **sequential-thinking** - Advanced reasoning for complex problems
- **memory** - Persistent knowledge graph across conversations

### Other MCPs
- **filesystem** - Enhanced file operations
- **neo4j-official** - Official Neo4j MCP server

## GCP MCP Setup

The GCP MCP server requires authentication:

```bash
# Authenticate with Application Default Credentials
gcloud auth application-default login

# Verify credentials exist
ls ~/.config/gcloud/application_default_credentials.json
```

Once authenticated, the GCP MCP provides tools for:
- **Cloud Run**: Deploy, manage, and monitor services/jobs
- **Cloud Scheduler**: Manage cron jobs
- **Cloud Logging**: Query and analyze logs
- **Cloud Build**: Check build status
- **Compute Engine**: Manage VMs
- **Secrets Manager**: Access secrets

## Docker MCP

No setup required. Provides tools for:
- List running containers
- Inspect container details
- View container logs
- Execute commands in containers
- Check Docker network/volume info

Perfect for debugging the local Neo4j container and Cloud Run builds.

## Adding New Skills

Create a new `.md` file in `.claude/skills/` with this structure:

```markdown
# Skill Name

Brief description of what this skill does.

## Overview

What problem does this solve?

## Steps

### 1. Step One

Description and commands...

### 2. Step Two

More steps...

## Related Skills

- Link to related skills

## Documentation

References to relevant docs
```

## Project Settings

`.claude/settings.local.json` contains:
- **Permission allowlist** - Pre-approved bash commands and tool calls
- **Enabled MCP servers** - Which MCPs are active for this project
- **Sandbox settings** - Currently disabled for development flexibility

## Tips

1. **Use skills for repetitive workflows** - Codify deployment, testing, and debugging procedures
2. **Leverage MCP tools** - Let Claude interact directly with GCP, Docker, and databases
3. **Update permissions as needed** - Add new bash patterns to the allowlist when developing
4. **Keep skills focused** - One skill per major workflow (deploy, test, debug, etc.)

## Learn More

- [Claude Code Documentation](https://claude.com/claude-code)
- [MCP Protocol Docs](https://modelcontextprotocol.io)
- [Creating Custom Skills](https://docs.anthropic.com/claude-code/skills)
