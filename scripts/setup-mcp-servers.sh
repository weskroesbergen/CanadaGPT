#!/bin/bash
set -e

# MCP Servers Installation Script for CanadaGPT
# This script installs and configures MCP servers for Claude Code

echo "========================================="
echo "CanadaGPT MCP Servers Installation"
echo "========================================="
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

echo "Detected OS: $OS"
echo "Detected Architecture: $ARCH"
echo ""

# Step 1: Download Neo4j MCP binary
echo "Step 1: Installing Neo4j MCP..."
echo "----------------------------------------"

NEO4J_VERSION="v0.1.14"  # Update this to latest version
CLAUDE_DIR="$HOME/.claude"
BIN_DIR="/usr/local/bin"

case "$OS" in
  Darwin)
    if [[ "$ARCH" == "arm64" ]]; then
      NEO4J_BINARY="neo4j-mcp-darwin-arm64"
    else
      NEO4J_BINARY="neo4j-mcp-darwin-amd64"
    fi
    ;;
  Linux)
    if [[ "$ARCH" == "x86_64" ]]; then
      NEO4J_BINARY="neo4j-mcp-linux-amd64"
    elif [[ "$ARCH" == "aarch64" ]]; then
      NEO4J_BINARY="neo4j-mcp-linux-arm64"
    else
      echo "Unsupported architecture: $ARCH"
      exit 1
    fi
    ;;
  *)
    echo "Unsupported OS: $OS"
    echo "Please download manually from: https://github.com/neo4j/mcp/releases"
    exit 1
    ;;
esac

echo "Downloading Neo4j MCP binary: $NEO4J_BINARY"
DOWNLOAD_URL="https://github.com/neo4j/mcp/releases/download/$NEO4J_VERSION/$NEO4J_BINARY"

if command -v curl &> /dev/null; then
  curl -L -o /tmp/neo4j-mcp "$DOWNLOAD_URL"
elif command -v wget &> /dev/null; then
  wget -O /tmp/neo4j-mcp "$DOWNLOAD_URL"
else
  echo "Error: Neither curl nor wget found. Please install one of them."
  exit 1
fi

chmod +x /tmp/neo4j-mcp

echo "Moving binary to $BIN_DIR (may require sudo)..."
sudo mv /tmp/neo4j-mcp "$BIN_DIR/"

# Verify installation
if neo4j-mcp -v &> /dev/null; then
  echo "✓ Neo4j MCP installed successfully"
  neo4j-mcp -v
else
  echo "✗ Neo4j MCP installation failed"
  exit 1
fi

echo ""

# Step 2: Create Claude Code configuration directory
echo "Step 2: Creating Claude Code configuration..."
echo "----------------------------------------"

mkdir -p "$CLAUDE_DIR"

# Step 3: Create MCP configuration
echo "Step 3: Configuring MCP servers..."
echo "----------------------------------------"

# Get project path
PROJECT_PATH="$(pwd)"

# Create config.json
cat > "$CLAUDE_DIR/config.json" << EOF
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
      "args": ["mcp-server-git", "--repository", "$PROJECT_PATH"]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "$PROJECT_PATH"
      ]
    }
  }
}
EOF

echo "✓ Configuration created at: $CLAUDE_DIR/config.json"
echo ""

# Step 4: Verify dependencies
echo "Step 4: Verifying dependencies..."
echo "----------------------------------------"

# Check for npx
if command -v npx &> /dev/null; then
  echo "✓ npx found"
else
  echo "✗ npx not found. Please install Node.js: https://nodejs.org/"
  exit 1
fi

# Check for uvx
if command -v uvx &> /dev/null; then
  echo "✓ uvx found"
else
  echo "⚠ uvx not found. Installing uv..."
  if command -v brew &> /dev/null; then
    brew install uv
  elif command -v curl &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    echo "✗ Could not install uv. Please install manually: https://docs.astral.sh/uv/"
    echo "  Or use Homebrew: brew install uv"
  fi
fi

# Verify uvx again
if command -v uvx &> /dev/null; then
  echo "✓ uvx is now available"
else
  echo "⚠ uvx not available. Git MCP server may not work."
  echo "  Please install uv manually: https://docs.astral.sh/uv/"
fi

echo ""

# Summary
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Installed MCP Servers:"
echo "  1. ✓ next-devtools-mcp (Next.js development)"
echo "  2. ✓ mcp-graphql (GraphQL queries)"
echo "  3. ✓ neo4j-mcp (Neo4j local)"
echo "  4. ✓ neo4j-mcp (Neo4j production - read-only)"
echo "  5. ✓ mcp-server-git (Git operations)"
echo "  6. ✓ @modelcontextprotocol/server-filesystem (File operations)"
echo ""
echo "Configuration saved to: $CLAUDE_DIR/config.json"
echo ""
echo "Next Steps:"
echo "  1. Restart Claude Code to load the new MCP servers"
echo "  2. Start your dev servers:"
echo "     - pnpm dev:frontend  (for Next.js DevTools)"
echo "     - pnpm dev:api       (for GraphQL MCP)"
echo "     - docker-compose up  (for Neo4j local)"
echo "  3. Test MCP tools in Claude Code"
echo ""
echo "Documentation: $PROJECT_PATH/MCP_SERVERS_SETUP.md"
echo ""
echo "For troubleshooting, see: https://github.com/neo4j/mcp"
echo "========================================="
