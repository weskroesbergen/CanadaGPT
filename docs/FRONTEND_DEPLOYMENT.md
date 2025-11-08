# CanadaGPT Frontend Deployment Guide

Complete guide for deploying the Next.js frontend to Google Cloud Run.

## Overview

The frontend is deployed as a containerized Next.js application on Google Cloud Run with:
- **Scale-to-zero**: 0 minimum instances (cost ~$5-10/month for light usage)
- **Auto-scaling**: Up to 10 instances during traffic spikes
- **Bilingual support**: EN/FR routing via next-intl
- **Supabase auth**: Integrated authentication
- **GraphQL API**: Connects to canadagpt-graph-api service

## Prerequisites

1. **GCP Authentication**
   ```bash
   gcloud auth login
   gcloud config set project canada-gpt-ca
   ```

2. **Docker Desktop**
   - Install from https://www.docker.com/products/docker-desktop
   - Ensure Docker is running

3. **Supabase Credentials**
   - Project URL (`NEXT_PUBLIC_SUPABASE_URL`)
   - Anon Key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`)
   - Get from: Supabase Dashboard → Project Settings → API

## Quick Deployment

### Option 1: Automated Script (Recommended)

```bash
cd /path/to/FedMCP
./scripts/deploy-frontend-cloudrun.sh
```

The script will:
1. Prompt for Supabase credentials
2. Build Docker image (~5-10 minutes)
3. Push to Artifact Registry
4. Deploy to Cloud Run
5. Display service URL

### Option 2: Manual Deployment

#### Step 1: Build Docker Image

```bash
cd /path/to/FedMCP

# Set build arguments
export NEXT_PUBLIC_GRAPHQL_URL="https://canadagpt-graph-api-213428056473.us-central1.run.app/graphql"
export NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
export NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
export NEXT_PUBLIC_BASE_URL="https://canadagpt.ca"

# Build image
docker build \
  --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_GRAPHQL_URL="${NEXT_PUBLIC_GRAPHQL_URL}" \
  --build-arg NEXT_PUBLIC_SUPABASE_URL="${NEXT_PUBLIC_SUPABASE_URL}" \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY="${NEXT_PUBLIC_SUPABASE_ANON_KEY}" \
  --build-arg NEXT_PUBLIC_BASE_URL="${NEXT_PUBLIC_BASE_URL}" \
  -t us-central1-docker.pkg.dev/canada-gpt-ca/canadagpt/canadagpt-frontend:latest \
  -f packages/frontend/Dockerfile \
  .
```

#### Step 2: Push to Artifact Registry

```bash
# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev

# Push image
docker push us-central1-docker.pkg.dev/canada-gpt-ca/canadagpt/canadagpt-frontend:latest
```

#### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy canadagpt-frontend \
  --image=us-central1-docker.pkg.dev/canada-gpt-ca/canadagpt/canadagpt-frontend:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=60 \
  --set-env-vars="NEXT_PUBLIC_GRAPHQL_URL=${NEXT_PUBLIC_GRAPHQL_URL},NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL},NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY},NEXT_PUBLIC_BASE_URL=${NEXT_PUBLIC_BASE_URL},NODE_ENV=production" \
  --port=3000
```

## Environment Variables

### Build-time Variables (Docker build args)
These are baked into the Docker image during build:

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_GRAPHQL_URL` | GraphQL API endpoint | `https://canadagpt-graph-api-213428056473.us-central1.run.app/graphql` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | `https://abcdefgh.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbGc...` |
| `NEXT_PUBLIC_BASE_URL` | Canonical URL for SEO | `https://canadagpt.ca` |

### Runtime Variables (Cloud Run env vars)
These can be updated without rebuilding the image:

```bash
gcloud run services update canadagpt-frontend \
  --region=us-central1 \
  --update-env-vars="NEXT_PUBLIC_GRAPHQL_URL=https://new-api-url.com/graphql"
```

## Testing Deployment

### 1. Health Check

```bash
SERVICE_URL=$(gcloud run services describe canadagpt-frontend --region=us-central1 --format='value(status.url)')
curl "${SERVICE_URL}/api/health"
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2025-11-07T...",
  "service": "canadagpt-frontend"
}
```

### 2. Test Bilingual Routing

```bash
# English version
curl -I "${SERVICE_URL}/en"

# French version
curl -I "${SERVICE_URL}/fr"
```

Both should return `200 OK`.

### 3. Test GraphQL Connection

Visit `${SERVICE_URL}/en/dashboard` and verify:
- Recent Hansard speeches load
- MP photos display correctly
- No console errors related to GraphQL

### 4. Test Supabase Auth

Visit `${SERVICE_URL}/en/profile` and verify:
- Redirects to login page
- After login, profile page loads

## Monitoring

### View Logs

```bash
# Recent logs
gcloud run services logs read canadagpt-frontend --region=us-central1 --limit=50

# Follow logs in real-time
gcloud run services logs tail canadagpt-frontend --region=us-central1

# Filter for errors only
gcloud run services logs read canadagpt-frontend --region=us-central1 --log-filter="severity>=ERROR"
```

### Check Service Status

```bash
gcloud run services describe canadagpt-frontend --region=us-central1
```

### Monitor Traffic

```bash
# Cloud Console
open "https://console.cloud.google.com/run/detail/us-central1/canadagpt-frontend/metrics?project=canada-gpt-ca"
```

## Scaling Configuration

### Current Settings
- **Min instances**: 0 (scale-to-zero enabled)
- **Max instances**: 10
- **Memory**: 512Mi
- **CPU**: 1
- **Timeout**: 60 seconds

### Adjust Scaling

**Enable always-on (eliminate cold starts):**
```bash
gcloud run services update canadagpt-frontend \
  --region=us-central1 \
  --min-instances=1
```
*Cost: ~$50-100/month*

**Increase max instances for high traffic:**
```bash
gcloud run services update canadagpt-frontend \
  --region=us-central1 \
  --max-instances=50
```

**Increase memory (if needed):**
```bash
gcloud run services update canadagpt-frontend \
  --region=us-central1 \
  --memory=1Gi
```

## Custom Domain Setup

### Step 1: Verify Domain Ownership

```bash
gcloud domains verify canadagpt.ca
```

### Step 2: Map Domain to Service

```bash
gcloud run domain-mappings create \
  --service=canadagpt-frontend \
  --domain=canadagpt.ca \
  --region=us-central1
```

### Step 3: Configure DNS

The command above will provide DNS records. Add them to your domain registrar:

**A Record:**
```
Type: A
Name: @
Value: 216.239.32.21
```

**AAAA Records:**
```
Type: AAAA
Name: @
Value: 2001:4860:4802:32::15
        2001:4860:4802:34::15
        2001:4860:4802:36::15
        2001:4860:4802:38::15
```

**Alternatively, use CNAME (for subdomains):**
```
Type: CNAME
Name: www
Value: ghs.googlehosted.com
```

### Step 4: Enable SSL

SSL is automatically provisioned by Cloud Run (takes ~15 minutes).

Check status:
```bash
gcloud run domain-mappings describe canadagpt.ca --region=us-central1
```

## Rollback

### Rollback to Previous Version

```bash
# List revisions
gcloud run revisions list --service=canadagpt-frontend --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic canadagpt-frontend \
  --region=us-central1 \
  --to-revisions=canadagpt-frontend-00005-abc=100
```

### Traffic Splitting (Blue/Green Deployment)

```bash
# Send 90% to latest, 10% to previous
gcloud run services update-traffic canadagpt-frontend \
  --region=us-central1 \
  --to-revisions=LATEST=90,canadagpt-frontend-00005-abc=10
```

## Troubleshooting

### Issue: Build Fails with "Cannot find module '@canadagpt/design-system'"

**Cause**: Workspace dependency not copied correctly.

**Fix**: Ensure Dockerfile copies entire `packages/` directory:
```dockerfile
COPY packages/design-system ./packages/design-system
COPY packages/frontend ./packages/frontend
```

### Issue: Cold Start Takes >10 Seconds

**Cause**: Scale-to-zero enabled, Next.js app cold start.

**Solutions**:
1. **Increase min instances** (costs more but eliminates cold starts)
2. **Use Cloud CDN** to cache static assets
3. **Implement app router streaming** (already enabled)

### Issue: 503 Service Unavailable

**Cause**: Deployment failed or health check failing.

**Fix**:
```bash
# Check logs
gcloud run services logs read canadagpt-frontend --region=us-central1 --limit=100

# Common issues:
# - Missing environment variables
# - Health check endpoint failing
# - Out of memory (increase to 1Gi)
```

### Issue: GraphQL Queries Fail

**Cause**: Incorrect GraphQL URL or CORS issue.

**Fix**:
```bash
# Verify environment variable
gcloud run services describe canadagpt-frontend --region=us-central1 --format="value(spec.template.spec.containers[0].env)"

# Update if needed
gcloud run services update canadagpt-frontend \
  --region=us-central1 \
  --update-env-vars="NEXT_PUBLIC_GRAPHQL_URL=https://correct-url.com/graphql"
```

## Cost Optimization

### Current Cost Estimate (Scale-to-zero)
- **Idle**: ~$0-1/month
- **Light usage** (100 requests/day): ~$5-10/month
- **Medium usage** (1000 requests/day): ~$15-25/month

### Cost Reduction Tips

1. **Keep scale-to-zero enabled** for staging/dev
2. **Use Cloud CDN** to cache static assets (_next/static)
3. **Optimize images** (already using next/image)
4. **Monitor logs** - excessive logging costs money

### Cost Increase for Production

**Enable always-on (min_instances=1):**
```bash
gcloud run services update canadagpt-frontend --region=us-central1 --min-instances=1
```
*Cost: ~$50-100/month, but eliminates cold starts*

## CI/CD Integration (Future)

### GitHub Actions Workflow

Create `.github/workflows/deploy-frontend.yml`:

```yaml
name: Deploy Frontend to Cloud Run

on:
  push:
    branches: [main]
    paths:
      - 'packages/frontend/**'
      - 'packages/design-system/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Google Auth
        uses: google-github-actions/auth@v1
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'

      - name: Deploy to Cloud Run
        run: |
          ./scripts/deploy-frontend-cloudrun.sh
        env:
          NEXT_PUBLIC_SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          NEXT_PUBLIC_SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
```

## Additional Resources

- **Cloud Run Documentation**: https://cloud.google.com/run/docs
- **Next.js Docker**: https://nextjs.org/docs/deployment#docker-image
- **Supabase Auth**: https://supabase.com/docs/guides/auth

## Support

For issues:
1. Check logs: `gcloud run services logs read canadagpt-frontend --region=us-central1 --limit=100`
2. Review Cloud Run metrics in GCP Console
3. Test health endpoint: `curl ${SERVICE_URL}/api/health`
