#!/bin/bash

# ============================================
# CanadaGPT API Key Generation Script
# ============================================
#
# This script generates cryptographically secure API keys and secrets
# for the CanadaGPT GraphQL API authentication system.
#
# Usage:
#   chmod +x scripts/generate-api-keys.sh
#   ./scripts/generate-api-keys.sh
#
# The generated keys should be:
# 1. Added to your local .env file for development
# 2. Stored in GCP Secret Manager for production
# 3. NEVER committed to git
# ============================================

echo ""
echo "🔐 CanadaGPT API Key Generator"
echo "======================================"
echo ""
echo "Generating secure API keys and secrets..."
echo ""

# Frontend API Key - used by the Next.js frontend
FRONTEND_API_KEY=$(openssl rand -hex 32)
echo "# Frontend API Key (10,000 requests/hour)"
echo "FRONTEND_API_KEY=$FRONTEND_API_KEY"
echo ""

# Public API Key - optional, for public read-only access
PUBLIC_API_KEY=$(openssl rand -hex 32)
echo "# Public API Key (1,000 requests/hour, read-only)"
echo "PUBLIC_API_KEY=$PUBLIC_API_KEY"
echo ""

# Admin API Key - for administrative operations
ADMIN_API_KEY=$(openssl rand -hex 32)
echo "# Admin API Key (50,000 requests/hour, full access)"
echo "ADMIN_API_KEY=$ADMIN_API_KEY"
echo ""

# JWT Secret - for Neo4jGraphQL authorization
JWT_SECRET=$(openssl rand -base64 32)
echo "# JWT Secret for Neo4jGraphQL"
echo "JWT_SECRET=$JWT_SECRET"
echo ""

# AUTH_SECRET - for NextAuth session encryption
AUTH_SECRET=$(openssl rand -base64 32)
echo "# NextAuth AUTH_SECRET (ROTATE THIS - compromised in previous builds)"
echo "AUTH_SECRET=$AUTH_SECRET"
echo ""

echo "======================================"
echo "✅ Keys generated successfully!"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Copy the keys above to your .env files:"
echo "   - Add FRONTEND_API_KEY, PUBLIC_API_KEY, ADMIN_API_KEY, JWT_SECRET to:"
echo "     packages/graph-api/.env"
echo "   - Add AUTH_SECRET to:"
echo "     packages/frontend/.env"
echo ""
echo "2. For production deployment:"
echo "   - Store these in GCP Secret Manager"
echo "   - See SECURITY_IMPLEMENTATION.md for instructions"
echo ""
echo "⚠️  SECURITY WARNING:"
echo "   - NEVER commit these keys to git"
echo "   - NEVER share these keys publicly"
echo "   - Rotate AUTH_SECRET immediately (previous builds leaked it)"
echo "   - Store production keys ONLY in Secret Manager"
echo ""
