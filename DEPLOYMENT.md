# Deployment Guide

**CRITICAL**: Read this entire document before deploying to production.

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Methods](#deployment-methods)
3. [Environment Variables](#environment-variables)
4. [Rollback Procedures](#rollback-procedures)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

**Before pushing to `main` (which auto-deploys):**

- [ ] Code review completed
- [ ] All tests passing locally (`pnpm test`, `pnpm type-check`)
- [ ] Design system built if changed (`pnpm --filter @canadagpt/design-system build`)
- [ ] No secrets or API keys hardcoded in code
- [ ] CLAUDE.md updated if architecture changed
- [ ] Database migrations tested (if applicable)
- [ ] Ready to monitor deployment for 15 minutes after

---

## Deployment Methods

### Method 1: Automatic (GitHub Actions) - RECOMMENDED

**Triggers**: Any push to `main` branch affecting:
- `packages/frontend/**`
- `packages/design-system/**`
- `.github/workflows/deploy-frontend.yml`

**What it does**:
1. Builds design-system package
2. Builds Docker image with build-time environment variables
3. Pushes to Artifact Registry
4. Deploys to Cloud Run (preserves existing env vars)

**Workflow**: `.github/workflows/deploy-frontend.yml`

**IMPORTANT**: The workflow only updates the container image. It does NOT modify environment variables or secrets. All configuration is preserved from the previous deployment.

### Method 2: Manual Deployment Script

**Use when**: GitHub Actions is down or you need more control

```bash
# From project root
./scripts/deploy-frontend-cloudrun.sh
```

**What it does**:
- Builds design-system locally
- Builds and pushes Docker image
- Deploys to Cloud Run with full environment variable configuration

**Prerequisites**:
- `gcloud` CLI authenticated (`gcloud auth login`)
- Docker running locally
- All secrets available in `.env` file

---

## Environment Variables

### Build-Time Variables (NEXT_PUBLIC_*)

These are **baked into the client JavaScript bundle** during Docker build:

| Variable | Source | Required |
|----------|--------|----------|
| `NEXT_PUBLIC_GRAPHQL_URL` | GitHub Secrets | Yes |
| `NEXT_PUBLIC_GRAPHQL_API_KEY` | GitHub Secrets | Yes |
| `NEXT_PUBLIC_SUPABASE_URL` | GitHub Secrets | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | GitHub Secrets | Yes |
| `NEXT_PUBLIC_BASE_URL` | Hardcoded | Yes |

**CRITICAL**: If you add a new `NEXT_PUBLIC_*` variable:
1. Add to GitHub Secrets
2. Add to `Dockerfile` ARG/ENV sections
3. Add to workflow `--build-arg` flags
4. Document here

### Runtime Variables (Server-only)

These are loaded at runtime from Cloud Run environment:

| Variable | Type | Required |
|----------|------|----------|
| `AUTH_TRUST_HOST` | Literal | Yes |
| `NEXTAUTH_URL` | Literal | Yes |
| `NODE_ENV` | Literal | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Secret | Yes |
| `AUTH_SECRET` | Secret | Yes |
| `GOOGLE_CLIENT_ID` | Secret | Yes |
| `GOOGLE_CLIENT_SECRET` | Secret | Yes |
| `GITHUB_CLIENT_ID` | Secret | Yes |
| `GITHUB_CLIENT_SECRET` | Secret | Yes |
| `FACEBOOK_CLIENT_ID` | Secret | Yes |
| `FACEBOOK_CLIENT_SECRET` | Secret | Yes |
| `LINKEDIN_CLIENT_ID` | Secret | Yes |
| `LINKEDIN_CLIENT_SECRET` | Secret | Yes |

**CRITICAL**: These are already configured in Cloud Run. The GitHub Actions workflow **DOES NOT** modify them. They persist across deployments.

### Viewing Current Configuration

```bash
# See all environment variables
gcloud run services describe canadagpt-frontend \
  --region=us-central1 \
  --format=yaml | grep -A 100 "env:"

# See specific variable
gcloud run services describe canadagpt-frontend \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env[?(@.name=='AUTH_TRUST_HOST')].value)"
```

---

## Rollback Procedures

### Quick Rollback (< 5 minutes old deployment)

```bash
# List recent revisions
gcloud run revisions list \
  --service=canadagpt-frontend \
  --region=us-central1 \
  --limit=5

# Rollback to previous revision
gcloud run services update-traffic canadagpt-frontend \
  --region=us-central1 \
  --to-revisions=canadagpt-frontend-00040-hlw=100
```

### Rollback via GitHub

1. Find the last working commit: `git log --oneline -10`
2. Revert the bad commit: `git revert <commit-hash>`
3. Push to main: `git push origin main`
4. GitHub Actions will auto-deploy the reverted code

### Emergency Rollback (Manual)

If GitHub Actions is broken:

```bash
# List image tags
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/canada-gpt-ca/canadagpt/frontend \
  --limit=10

# Deploy specific known-good image
gcloud run deploy canadagpt-frontend \
  --image us-central1-docker.pkg.dev/canada-gpt-ca/canadagpt/frontend:737649e22da4cc4ecf91168a7b9b85f13b50d98d \
  --region=us-central1 \
  --platform=managed
```

---

## Post-Deployment Verification

**REQUIRED**: Monitor for 15 minutes after deployment completes.

### 1. Check Deployment Status

```bash
# Watch the GitHub Actions run
gh run list --limit 1
gh run view $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

# Check Cloud Run revision
gcloud run services describe canadagpt-frontend \
  --region=us-central1 \
  --format="value(status.latestReadyRevisionName,status.url)"
```

### 2. Smoke Tests (Run All)

```bash
# Homepage
curl -sL https://canadagpt.ca/ | grep -o "<title>.*</title>"
# Expected: <title>CanadaGPT - Canadian Government...

# MPs Page
curl -sL https://canadagpt.ca/en/mps | grep -o "Browse all 343 current MPs"
# Expected: Browse all 343 current MPs

# Bills Page
curl -sL https://canadagpt.ca/en/bills | grep -o "Bills & Legislation"
# Expected: Bills & Legislation

# Debates Page
curl -sL https://canadagpt.ca/en/debates | grep -o "Hansard Debates"
# Expected: Hansard Debates

# Auth Endpoint (500 is expected for unauthenticated)
curl -s -o /dev/null -w "%{http_code}\n" https://canadagpt.ca/api/auth/session
# Expected: 500 or 200

# GraphQL API
curl -s -X POST https://canadagpt-graph-api-213428056473.us-central1.run.app/graphql \
  -H "Content-Type: application/json" \
  -H "x-api-key: 9587c9820b109977a43a9302c23d051d98eff56050581eab63784b0b7f08152d" \
  -d '{"query":"{ mps(options: {limit: 1}) { id name } }"}' | jq .
# Expected: {"data":{"mps":[...]}}
```

### 3. Check Logs for Errors

```bash
# Frontend errors (last 5 minutes)
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=canadagpt-frontend \
  AND severity>=ERROR \
  AND timestamp>=\"$(date -u -v-5M '+%Y-%m-%dT%H:%M:%SZ')\"" \
  --limit=20 --format=json | jq -r '.[].textPayload // .[].jsonPayload.message // empty'

# Graph API errors
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=canadagpt-graph-api \
  AND severity>=ERROR" \
  --limit=20
```

### 4. Manual Browser Tests

- [ ] Visit https://canadagpt.ca/ - homepage loads
- [ ] Click "MPs" - MPs grid loads with photos
- [ ] Click "Bills" - bills list loads
- [ ] Click "Debates" - debates list loads
- [ ] Sign in with Google - auth works
- [ ] Chat widget - opens and can send messages (if signed in)

---

## Troubleshooting

### Issue: "Failed to load MPs/Bills/Debates"

**Symptoms**: GraphQL queries failing in browser

**Common Causes**:
1. `NEXT_PUBLIC_GRAPHQL_API_KEY` missing from build
2. Graph API service down
3. Neo4j database connection issue

**Fix**:
```bash
# Check if API key is in the build
curl -sL https://canadagpt.ca/ | grep -o "NEXT_PUBLIC_GRAPHQL_API_KEY"
# Should NOT appear (it's in bundle, not HTML)

# Check Graph API
curl -s -X POST https://canadagpt-graph-api-213428056473.us-central1.run.app/graphql \
  -H "Content-Type: application/json" \
  -H "x-api-key: 9587c9820b109977a43a9302c23d051d98eff56050581eab63784b0b7f08152d" \
  -d '{"query":"{ mps(options: {limit: 1}) { id name } }"}'
```

### Issue: "UntrustedHost" Auth Errors

**Symptoms**: Cannot sign in, auth errors in logs

**Cause**: `AUTH_TRUST_HOST` or `NEXTAUTH_URL` missing/incorrect

**Fix**:
```bash
# Check environment variables
gcloud run services describe canadagpt-frontend --region=us-central1 \
  --format=yaml | grep -E "AUTH_TRUST_HOST|NEXTAUTH_URL"

# Should show:
# - name: AUTH_TRUST_HOST
#   value: 'true'
# - name: NEXTAUTH_URL
#   value: https://canadagpt.ca
```

### Issue: Build Fails in GitHub Actions

**Symptoms**: Red X on commit, Docker build errors

**Common Causes**:
1. Design system not building
2. Missing TypeScript types
3. Out of memory during build

**Fix**:
```bash
# View build logs
gh run view $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') --log-failed

# Test locally
pnpm install
pnpm --filter @canadagpt/design-system build
cd packages/frontend && pnpm build
```

### Issue: Deployment Succeeds But Site Broken

**CRITICAL**: This means the deployment workflow modified environment variables

**Emergency Fix**:
```bash
# Immediately rollback
gcloud run revisions list --service=canadagpt-frontend --region=us-central1 --limit=5

# Deploy previous working revision
gcloud run services update-traffic canadagpt-frontend \
  --region=us-central1 \
  --to-revisions=<PREVIOUS_WORKING_REVISION>=100
```

**Root Cause Fix**: Check the GitHub Actions workflow for `--set-env-vars` or `--update-secrets` flags. These should NOT be present - the workflow should only update the image:

```yaml
# CORRECT (what we have now)
gcloud run deploy canadagpt-frontend \
  --image <image> \
  --region us-central1 \
  --allow-unauthenticated

# WRONG (this breaks everything)
gcloud run deploy canadagpt-frontend \
  --image <image> \
  --set-env-vars="FOO=bar"  # ❌ Replaces ALL env vars!
```

---

## Adding GitHub Secrets

When adding new build-time environment variables:

```bash
# Via GitHub CLI
gh secret set NEXT_PUBLIC_NEW_VAR --body "value"

# Via GitHub UI
# 1. Go to repo Settings > Secrets and variables > Actions
# 2. Click "New repository secret"
# 3. Name: NEXT_PUBLIC_NEW_VAR
# 4. Value: <your-value>
# 5. Click "Add secret"
```

---

## Deployment Frequency

- **Automatic**: Every push to `main`
- **Typical**: 5-10 times per day
- **Build time**: ~3-4 minutes
- **Zero downtime**: Cloud Run handles rollout

---

## Support

**Deployment Issues**: Check logs first, then rollback if critical

**Questions**: See CLAUDE.md for architecture documentation

**Emergency**: Rollback immediately, investigate later
