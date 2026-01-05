# Deploy Production

This skill deploys the CanadaGPT application to Google Cloud Run production environment.

## Overview

Deploys the Graph API and Frontend services to Cloud Run with pre-deployment validation and post-deployment verification.

## Steps

### 1. Pre-Deployment Validation

Run comprehensive checks before deploying:

```bash
# Type check all packages
pnpm --filter @canadagpt/frontend type-check
pnpm --filter @canadagpt/graph-api type-check

# Build all packages to catch errors
pnpm build:all

# Check for uncommitted changes
git status
```

**Stop if:**
- Type errors exist
- Build fails
- Uncommitted changes present (unless intentional hotfix)

### 2. Deploy Graph API

Deploy the Neo4j GraphQL API service:

```bash
./scripts/deploy-cloud-run.sh
```

**What this does:**
- Builds Docker image with platform `linux/amd64`
- Pushes to Artifact Registry: `us-central1-docker.pkg.dev/canada-gpt-ca/canadagpt/graph-api`
- Deploys to Cloud Run service: `canadagpt-graph-api`
- Sets environment variables (Neo4j connection, API keys)
- Configures VPC connector for Neo4j access

**Monitor:**
```bash
# Watch build progress
gcloud builds list --limit=1

# Check service status
gcloud run services describe canadagpt-graph-api --region=us-central1
```

### 3. Deploy Frontend

Deploy the Next.js application:

```bash
./scripts/deploy-frontend-cloudrun.sh
```

**What this does:**
- Builds Next.js production bundle
- Creates Docker image
- Deploys to Cloud Run: `canadagpt-frontend`
- Sets Supabase, authentication, and API environment variables

### 4. Verify Deployments

Test deployed services:

```bash
# Check Graph API health
curl https://canadagpt-graph-api-1062802561472.us-central1.run.app/health

# Check Frontend
curl https://canadagpt.ca

# View recent logs for errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=canadagpt-graph-api" --limit=20 --format=json

gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=canadagpt-frontend" --limit=20 --format=json
```

**Smoke tests:**
- Visit https://canadagpt.ca in browser
- Test GraphQL query in playground
- Verify Neo4j connection (check a debate page)
- Test authentication flow
- Check mobile responsiveness

### 5. Tag Release

If deployment successful:

```bash
# Tag the release
git tag -a v$(date +%Y%m%d-%H%M) -m "Production deployment $(date +%Y-%m-%d)"
git push origin --tags
```

## Rollback Procedure

If issues detected:

```bash
# Rollback Graph API
gcloud run services update-traffic canadagpt-graph-api \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1

# Rollback Frontend
gcloud run services update-traffic canadagpt-frontend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1

# List revisions to find previous version
gcloud run revisions list --service=canadagpt-graph-api --region=us-central1
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Build timeout | Large image size | Check .dockerignore, optimize layers |
| Neo4j connection fails | VPC connector issue | Verify `--vpc-connector=canadagpt-vpc-connector` |
| GraphQL schema errors | Schema/DB mismatch | Check Neo4j indexes/constraints |
| Frontend 500 errors | Missing env vars | Verify secrets in Cloud Run config |

## Notes

- **Platform**: Always build with `--platform linux/amd64` for Cloud Run
- **Secrets**: Use GCP Secret Manager for sensitive values
- **Zero Downtime**: Cloud Run handles traffic migration automatically
- **Costs**: Cloud Run charges per request + CPU time
- **Region**: All services in `us-central1` for Neo4j proximity

## Related Skills

- `/deploy-ingestion` - Deploy data pipeline jobs
- `/check-data-freshness` - Verify production data quality

## Documentation

See `DEPLOYMENT.md` for detailed deployment procedures and troubleshooting.
