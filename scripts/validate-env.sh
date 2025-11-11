#!/bin/bash
# Environment Variable Validation Script
# Validates required environment variables before deployment

set -euo pipefail

SERVICE=$1
ENV=${2:-production}

if [ -z "$SERVICE" ]; then
  echo "Usage: $0 <service> [environment]"
  echo "Example: $0 graph-api production"
  exit 1
fi

echo "🔍 Validating $SERVICE configuration for $ENV environment..."
echo ""

validate_url() {
  local url=$1
  local var_name=$2

  if [[ ! $url =~ ^https?:// ]]; then
    echo "❌ Invalid URL format for $var_name: $url"
    echo "   Must start with http:// or https://"
    return 1
  fi
  return 0
}

case $SERVICE in
  graph-api)
    echo "📋 Checking graph-api environment variables..."

    # Check required vars
    if [ -z "${NEO4J_URI:-}" ]; then
      echo "❌ ERROR: NEO4J_URI not set"
      exit 1
    fi
    echo "✅ NEO4J_URI: $NEO4J_URI"

    if [ -z "${NEO4J_PASSWORD:-}" ]; then
      echo "❌ ERROR: NEO4J_PASSWORD not set"
      exit 1
    fi
    echo "✅ NEO4J_PASSWORD: [REDACTED]"

    # Validate CORS origins format
    if [ -n "${CORS_ORIGINS:-}" ]; then
      echo ""
      echo "🌐 Validating CORS_ORIGINS..."

      # Split on both comma and semicolon
      IFS=';,' read -ra ORIGINS <<< "$CORS_ORIGINS"

      if [ ${#ORIGINS[@]} -eq 0 ]; then
        echo "❌ CORS_ORIGINS is empty after parsing"
        exit 1
      fi

      for origin in "${ORIGINS[@]}"; do
        # Trim whitespace
        origin=$(echo "$origin" | xargs)

        if [ -z "$origin" ]; then
          continue
        fi

        if ! validate_url "$origin" "CORS_ORIGINS"; then
          exit 1
        fi
        echo "   ✅ $origin"
      done

      echo "✅ CORS origins valid (${#ORIGINS[@]} origins)"
    else
      echo "⚠️  WARNING: CORS_ORIGINS not set, will use default"
    fi
    ;;

  frontend)
    echo "📋 Checking frontend environment variables..."

    if [ -z "${NEXT_PUBLIC_GRAPHQL_URL:-}" ]; then
      echo "❌ ERROR: NEXT_PUBLIC_GRAPHQL_URL not set"
      exit 1
    fi

    if ! validate_url "$NEXT_PUBLIC_GRAPHQL_URL" "NEXT_PUBLIC_GRAPHQL_URL"; then
      exit 1
    fi
    echo "✅ NEXT_PUBLIC_GRAPHQL_URL: $NEXT_PUBLIC_GRAPHQL_URL"

    if [ -z "${NEXT_PUBLIC_SUPABASE_URL:-}" ]; then
      echo "❌ ERROR: NEXT_PUBLIC_SUPABASE_URL not set"
      exit 1
    fi

    if ! validate_url "$NEXT_PUBLIC_SUPABASE_URL" "NEXT_PUBLIC_SUPABASE_URL"; then
      exit 1
    fi
    echo "✅ NEXT_PUBLIC_SUPABASE_URL: $NEXT_PUBLIC_SUPABASE_URL"

    if [ -z "${AUTH_SECRET:-}" ]; then
      echo "❌ ERROR: AUTH_SECRET not set"
      exit 1
    fi
    echo "✅ AUTH_SECRET: [REDACTED]"
    ;;

  *)
    echo "❌ Unknown service: $SERVICE"
    echo "Supported services: graph-api, frontend"
    exit 1
    ;;
esac

echo ""
echo "✅ All $SERVICE environment variables validated successfully!"
