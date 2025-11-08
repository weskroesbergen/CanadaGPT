# CanadaGPT - GCP Infrastructure with Terraform

This directory contains Terraform configuration for deploying CanadaGPT infrastructure on Google Cloud Platform.

---

## 📋 Prerequisites

### 1. Software Requirements
- **Terraform** 1.6+ ([Download](https://www.terraform.io/downloads))
- **gcloud CLI** ([Install](https://cloud.google.com/sdk/docs/install))
- **GCP Account** with billing enabled

### 2. GCP Project Setup

```bash
# Create new GCP project (or use existing)
gcloud projects create canadagpt-production --name="CanadaGPT Production"

# Set as default project
gcloud config set project canadagpt-production

# Enable billing (required - do this via GCP Console)
# https://console.cloud.google.com/billing

# Authenticate for Terraform
gcloud auth application-default login
```

### 3. Neo4j Aura Setup

**Option A: GCP Marketplace (Recommended)**
1. Go to [Neo4j Aura on GCP Marketplace](https://console.cloud.google.com/marketplace/product/endpoints/prod.n4gcp.neo4j.io)
2. Subscribe to **Neo4j Aura Professional**
3. Create instance:
   - **Size**: 4GB memory (beta), 8GB (production)
   - **Region**: Same as your GCP region (e.g., us-central1)
   - **Cloud**: Google Cloud
   - **Enable Private Service Connect**: Yes
4. Save connection details:
   - URI: `neo4j+s://xxxxx.databases.neo4j.io`
   - Password: (save securely)

**Option B: Direct Signup**
1. Go to [aura.neo4j.io](https://aura.neo4j.io/)
2. Create account
3. Create AuraDB Professional instance
4. Follow same configuration as Option A

**Cost:**
- Beta (4GB): $259/month (pause when not testing = $52/month, 80% savings)
- Production (8GB): $518/month

---

## 🚀 Quick Start

### 1. Configure Variables

```bash
# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required values:**
```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"  # Or northamerica-northeast1 (Montreal)
neo4j_uri  = "neo4j+s://xxxxx.databases.neo4j.io"  # From Neo4j Aura
```

### 2. Initialize Terraform

```bash
terraform init
```

This downloads required providers (~30 seconds).

### 3. Plan Infrastructure

```bash
terraform plan
```

**Review the plan carefully.** You should see:
- ✅ ~15-20 resources to create
- ✅ VPC, Serverless VPC Connector, Cloud NAT
- ✅ 3 Service Accounts (frontend, API, pipeline)
- ✅ 2 Secrets (neo4j-password, canlii-api-key)
- ✅ 1 Artifact Registry repository
- ❌ No resources to destroy

### 4. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted.

**Expected duration:** 3-5 minutes

**What gets created:**
1. **VPC Network** (`canadagpt-vpc`)
2. **Serverless VPC Connector** (`canadagpt-vpc-connector`)
3. **Cloud NAT** (for outbound API calls to government sources)
4. **Service Accounts**:
   - `canadagpt-frontend@PROJECT_ID.iam.gserviceaccount.com`
   - `canadagpt-api@PROJECT_ID.iam.gserviceaccount.com`
   - `canadagpt-pipeline@PROJECT_ID.iam.gserviceaccount.com`
5. **Secrets** (empty, you'll add values next):
   - `neo4j-password`
   - `canlii-api-key`
6. **Artifact Registry**: `REGION-docker.pkg.dev/PROJECT_ID/canadagpt`

### 5. Add Secrets

```bash
# Neo4j password (REQUIRED)
echo -n "YOUR_NEO4J_PASSWORD" | gcloud secrets versions add neo4j-password --data-file=-

# CanLII API key (optional - only if you have one)
echo -n "YOUR_CANLII_API_KEY" | gcloud secrets versions add canlii-api-key --data-file=-
```

**Get CanLII API Key (free for research):**
- Request: https://www.canlii.org/en/feedback/feedback.html
- Use case: "Research on Canadian government accountability"
- Approval: Usually within 1-2 business days

### 6. Verify Deployment

```bash
# Check VPC Connector
gcloud compute networks vpc-access connectors list --region=us-central1

# Check Service Accounts
gcloud iam service-accounts list

# Check Secrets
gcloud secrets list

# Check Artifact Registry
gcloud artifacts repositories list
```

---

## 📊 Cost Breakdown

### Beta Environment (Scale-to-Zero)

| Resource | Monthly Cost | Notes |
|----------|--------------|-------|
| **Neo4j Aura 4GB** | $259 ($52 paused) | Pause when not testing (80% savings) |
| **VPC Connector** | $25 | e2-micro, 2-3 instances |
| **Cloud NAT** | $45 | Outbound for gov API calls |
| **Artifact Registry** | $0.10/GB | ~$0.50 for 5 Docker images |
| **Secret Manager** | $0.30 | 2 secrets, 300k accesses/month |
| **Cloud Run** | $5-15 | Scale-to-zero, minimal usage |
| **Total (Active)** | **~$335-355/month** | |
| **Total (Paused)** | **~$130-150/month** | 80% savings by pausing Neo4j |

### Production Environment (Always-On)

| Resource | Monthly Cost | Notes |
|----------|--------------|-------|
| **Neo4j Aura 8GB** | $518 | Upgraded instance |
| **VPC Connector** | $25 | Same |
| **Cloud NAT** | $50 | Higher bandwidth |
| **Cloud Run (Frontend)** | $105 | min_instances=1 |
| **Cloud Run (API)** | $200 | min_instances=2 |
| **Cloud CDN** | $20 | Static assets |
| **Logging** | $25 | 50GB/month |
| **Monitoring** | $15 | Metrics + alerting |
| **Total** | **~$958/month** | |

---

## 🔒 Security

### Service Account Permissions

**Frontend SA** (`canadagpt-frontend@`):
- ✅ Read from Artifact Registry
- ✅ Invoke API service (internal)
- ❌ No secret access (frontend is public)

**API SA** (`canadagpt-api@`):
- ✅ Read from Artifact Registry
- ✅ Read `neo4j-password` secret
- ❌ No public access (internal only)

**Pipeline SA** (`canadagpt-pipeline@`):
- ✅ Read from Artifact Registry
- ✅ Read `neo4j-password` secret
- ✅ Read `canlii-api-key` secret
- ❌ No public access (triggered by Cloud Scheduler)

### Private Service Connect

Neo4j Aura connects via **Private Service Connect**, meaning:
- ✅ No public internet exposure
- ✅ Traffic stays within Google network
- ✅ Cloud Run services access Neo4j via VPC Connector
- ❌ Cannot access Neo4j from your laptop (use Neo4j Aura console for admin)

### Secrets Management

- ✅ All secrets encrypted at rest (AES-256)
- ✅ Access logged in Cloud Audit Logs
- ✅ IAM-based access control
- ❌ Never commit terraform.tfvars (contains neo4j_uri)

---

## 🛠️ Management

### View Outputs

```bash
terraform output

# Example output:
# project_id = "canadagpt-production"
# region = "us-central1"
# vpc_connector_id = "projects/.../locations/us-central1/connectors/canadagpt-vpc-connector"
# artifact_registry_url = "us-central1-docker.pkg.dev/canadagpt-production/canadagpt"
# service_accounts = {
#   api = "canadagpt-api@canadagpt-production.iam.gserviceaccount.com"
#   frontend = "canadagpt-frontend@canadagpt-production.iam.gserviceaccount.com"
#   pipeline = "canadagpt-pipeline@canadagpt-production.iam.gserviceaccount.com"
# }
```

### Update Infrastructure

```bash
# Make changes to .tf files
nano main.tf

# Review changes
terraform plan

# Apply updates
terraform apply
```

### Pause Neo4j (Save 80% Costs)

```bash
# Pause via Neo4j Aura console
# https://console.neo4j.io/

# Or via API (requires Neo4j API key)
curl -X POST https://api.neo4j.io/v1/instances/YOUR_INSTANCE_ID/pause \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Resume:**
```bash
curl -X POST https://api.neo4j.io/v1/instances/YOUR_INSTANCE_ID/resume \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Destroy Infrastructure

**⚠️ WARNING: This deletes all resources! Data in Neo4j will be lost unless you export it first.**

```bash
# Export Neo4j data first (via Aura console)
# 1. Go to https://console.neo4j.io/
# 2. Select instance → Export → Download dump

# Then destroy Terraform-managed resources
terraform destroy
```

**What gets deleted:**
- ✅ VPC, NAT, Service Accounts, Secrets (empty shells)
- ❌ Neo4j Aura instance (managed separately)
- ❌ Docker images in Artifact Registry (if any exist)
- ❌ Logs in Cloud Logging

---

## 🔍 Troubleshooting

### Issue: "API not enabled"

**Error:**
```
Error: Error creating Network: googleapi: Error 403: Compute Engine API has not been used...
```

**Fix:**
```bash
# Enable manually (Terraform will do this, but can take 1-2 min)
gcloud services enable compute.googleapis.com
terraform apply
```

### Issue: "Insufficient Permission"

**Error:**
```
Error: Error creating Service Account: googleapi: Error 403: Permission denied
```

**Fix:**
```bash
# Grant yourself Owner role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL@gmail.com" \
  --role="roles/owner"
```

### Issue: VPC Connector Creation Timeout

**Symptoms:** VPC Connector takes >10 minutes, eventually times out

**Fix:**
```bash
# Delete failed connector
gcloud compute networks vpc-access connectors delete canadagpt-vpc-connector \
  --region=us-central1

# Re-apply
terraform apply
```

### Issue: Neo4j Connection Refused

**Symptoms:** Cloud Run service can't connect to Neo4j

**Checklist:**
- ✅ Is Neo4j instance running (not paused)?
- ✅ Is Private Service Connect enabled in Neo4j Aura?
- ✅ Is Cloud Run service using VPC Connector? (`vpc_access` in terraform)
- ✅ Is `neo4j-password` secret correctly set?

**Test connection:**
```bash
# From Cloud Shell (won't work - needs VPC)
# Instead, deploy a test Cloud Run service with netcat:
gcloud run deploy neo4j-test \
  --image=alpine \
  --command=sh \
  --args=-c,"apk add netcat-openbsd && nc -zv YOUR_NEO4J_HOST 7687" \
  --vpc-connector=canadagpt-vpc-connector \
  --region=us-central1
```

---

## 📚 Next Steps

After infrastructure is deployed:

1. **Phase 1.3**: Set up Neo4j schema
   ```bash
   cd ../docs
   # Follow neo4j-schema.cypher (to be created)
   ```

2. **Phase 2**: Build data pipeline
   ```bash
   cd ../packages/data-pipeline
   # Build Python ingestion scripts
   ```

3. **Phase 3**: Deploy GraphQL API
   ```bash
   cd ../packages/graph-api
   npm run build
   # Deploy to Cloud Run
   ```

4. **Phase 4**: Deploy frontend
   ```bash
   cd ../packages/frontend
   npm run build
   # Deploy to Cloud Run
   ```

---

## 📖 Resources

- [Terraform GCP Provider Docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Serverless VPC Access](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access)
- [Neo4j Aura Documentation](https://neo4j.com/docs/aura/)
- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)

---

## 🐛 Support

- **Terraform Issues**: [GitHub Issues](https://github.com/yourusername/FedMCP/issues)
- **GCP Support**: https://cloud.google.com/support
- **Neo4j Support**: https://support.neo4j.com/

---

**Created for CanadaGPT by Matthew Dufresne**
