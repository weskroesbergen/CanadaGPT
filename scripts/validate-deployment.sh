#!/bin/bash
# Pre-deployment validation script
# Run this before deploying to catch configuration issues

set -e

echo "🔍 Validating deployment configuration..."
echo ""

ERRORS=0

# Check 1: Verify workflow doesn't have --set-env-vars or --update-secrets
echo "✓ Checking GitHub Actions workflow..."
if grep -q "\-\-set-env-vars" .github/workflows/deploy-frontend.yml; then
  echo "❌ ERROR: deploy-frontend.yml contains --set-env-vars"
  echo "   This will REPLACE all environment variables and break production!"
  echo "   Remove this flag - the workflow should only update the image."
  ((ERRORS++))
fi

if grep -q "\-\-update-secrets" .github/workflows/deploy-frontend.yml; then
  echo "❌ ERROR: deploy-frontend.yml contains --update-secrets"
  echo "   This will REPLACE secret references and break production!"
  echo "   Remove this flag - the workflow should only update the image."
  ((ERRORS++))
fi

if [ $ERRORS -eq 0 ]; then
  echo "   ✅ Workflow only updates image (correct)"
fi
echo ""

# Check 2: Verify all NEXT_PUBLIC_ build args are in workflow
echo "✓ Checking NEXT_PUBLIC_ build arguments..."
DOCKERFILE="packages/frontend/Dockerfile"
WORKFLOW=".github/workflows/deploy-frontend.yml"

# Extract ARG NEXT_PUBLIC_ from Dockerfile
DOCKERFILE_ARGS=$(grep "^ARG NEXT_PUBLIC_" $DOCKERFILE | sed 's/ARG //' | sort)

# Extract --build-arg NEXT_PUBLIC_ from workflow
WORKFLOW_ARGS=$(grep "\-\-build-arg NEXT_PUBLIC_" $WORKFLOW | sed 's/.*--build-arg //' | sed 's/=.*//' | sort)

if [ "$DOCKERFILE_ARGS" != "$WORKFLOW_ARGS" ]; then
  echo "❌ ERROR: Mismatch between Dockerfile and workflow build args"
  echo ""
  echo "Dockerfile ARGs:"
  echo "$DOCKERFILE_ARGS"
  echo ""
  echo "Workflow --build-args:"
  echo "$WORKFLOW_ARGS"
  echo ""
  echo "These must match exactly!"
  ((ERRORS++))
else
  echo "   ✅ All NEXT_PUBLIC_ variables present in both"
fi
echo ""

# Check 3: Verify design-system build step exists
echo "✓ Checking design-system build step..."
if ! grep -q "pnpm --filter @canadagpt/design-system build" $WORKFLOW; then
  echo "❌ ERROR: Workflow missing design-system build step"
  echo "   Docker build will fail without packages/design-system/dist"
  ((ERRORS++))
else
  echo "   ✅ Design-system build step present"
fi
echo ""

# Check 4: TypeScript compilation
echo "✓ Checking TypeScript..."
cd packages/frontend
if ! pnpm type-check > /dev/null 2>&1; then
  echo "❌ ERROR: TypeScript errors in frontend"
  echo "   Run 'pnpm --filter @canadagpt/frontend type-check' to see details"
  ((ERRORS++))
else
  echo "   ✅ No TypeScript errors"
fi
cd ../..
echo ""

# Check 5: Verify Cloud Run service exists
echo "✓ Checking Cloud Run service..."
if ! gcloud run services describe canadagpt-frontend --region=us-central1 > /dev/null 2>&1; then
  echo "⚠️  WARNING: Cannot reach Cloud Run service (may not be authenticated)"
else
  echo "   ✅ Cloud Run service accessible"

  # Check current environment variables
  CURRENT_ENV_VARS=$(gcloud run services describe canadagpt-frontend --region=us-central1 --format=yaml | grep -E "name: (AUTH_TRUST_HOST|NEXTAUTH_URL|NODE_ENV)" | wc -l | tr -d ' ')

  if [ "$CURRENT_ENV_VARS" -lt 3 ]; then
    echo "⚠️  WARNING: Expected environment variables may be missing from Cloud Run"
    echo "   Check with: gcloud run services describe canadagpt-frontend --region=us-central1"
  else
    echo "   ✅ Core environment variables present"
  fi
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
  echo "✅ All checks passed! Safe to deploy."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
else
  echo "❌ $ERRORS error(s) found. DO NOT DEPLOY."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Fix these issues before deploying to production."
  echo "See DEPLOYMENT.md for troubleshooting guidance."
  exit 1
fi
