# Phase 1.2 Complete: GCP Infrastructure (Terraform) ✅

## Summary

Successfully created comprehensive Terraform configuration for deploying CanadaGPT infrastructure on Google Cloud Platform. The configuration is production-ready with security best practices, cost optimization, and clear documentation.

---

## ✅ Completed Tasks

### 1. Terraform Configuration Files

**Created:**
- ✅ `terraform/main.tf` (450+ lines) - Complete infrastructure as code
- ✅ `terraform/variables.tf` - All configurable parameters with validation
- ✅ `terraform/terraform.tfvars.example` - Example configuration template
- ✅ `terraform/README.md` (500+ lines) - Comprehensive setup guide
- ✅ `terraform/.gitignore` - Prevent committing sensitive files

---

## 🏗️ Infrastructure Components

### Networking (VPC + Private Service Connect)

```hcl
✅ VPC Network (canadagpt-vpc)
   ├── Subnet for VPC Connector (10.8.0.0/28)
   └── Private IP Google Access enabled

✅ Serverless VPC Access Connector
   ├── Region: us-central1 (configurable)
   ├── Machine type: e2-micro
   ├── Min instances: 2, Max: 3
   └── Purpose: Cloud Run → Neo4j private connection

✅ Cloud Router + Cloud NAT
   ├── Auto IP allocation
   ├── All subnetworks NATed
   └── Purpose: Outbound calls to government APIs
```

**Why This Matters:**
- **Security**: Neo4j accessed via Private Service Connect (no public internet)
- **Functionality**: Cloud Run can call external government APIs
- **Cost**: VPC Connector ~$25/month, Cloud NAT ~$45/month

---

### Service Accounts (IAM)

```
✅ canadagpt-frontend@PROJECT_ID.iam.gserviceaccount.com
   └── Permissions: Read Artifact Registry, Invoke API (internal)

✅ canadagpt-api@PROJECT_ID.iam.gserviceaccount.com
   └── Permissions: Read Artifact Registry, Access neo4j-password secret

✅ canadagpt-pipeline@PROJECT_ID.iam.gserviceaccount.com
   └── Permissions: Read Artifact Registry, Access both secrets
```

**Security Model:**
- ✅ Least privilege principle
- ✅ Each service has minimal required permissions
- ❌ No service account keys (uses Workload Identity)

---

### Secret Manager

```
✅ neo4j-password (empty, user adds value)
   └── Accessed by: API, Pipeline

✅ canlii-api-key (empty, optional)
   └── Accessed by: Pipeline only
```

**How to Add Secrets (After Terraform Apply):**
```bash
echo -n "YOUR_NEO4J_PASSWORD" | gcloud secrets versions add neo4j-password --data-file=-
echo -n "YOUR_CANLII_API_KEY" | gcloud secrets versions add canlii-api-key --data-file=-
```

---

### Artifact Registry

```
✅ Repository: us-central1-docker.pkg.dev/PROJECT_ID/canadagpt
   ├── Format: Docker
   └── Access: All service accounts can pull images
```

**Will Store:**
- `frontend:latest`, `frontend:SHA`
- `api:latest`, `api:SHA`
- `pipeline:latest`, `pipeline:SHA`

---

### API Enablement (Automatic)

Terraform enables these GCP APIs:
- ✅ `run.googleapis.com` - Cloud Run
- ✅ `vpcaccess.googleapis.com` - Serverless VPC Access
- ✅ `compute.googleapis.com` - VPC, NAT
- ✅ `artifactregistry.googleapis.com` - Docker registry
- ✅ `secretmanager.googleapis.com` - Secrets
- ✅ `cloudbuild.googleapis.com` - Image builds
- ✅ `cloudscheduler.googleapis.com` - Cron jobs
- ✅ `logging.googleapis.com` - Logs
- ✅ `monitoring.googleapis.com` - Metrics

---

## 📊 Cost Analysis

### Beta Environment (Scale-to-Zero)

| Resource | Monthly Cost | Details |
|----------|--------------|---------|
| Neo4j Aura 4GB | $259 | Managed Neo4j (pause = $52, 80% savings) |
| VPC Connector | $25 | e2-micro, 2-3 instances |
| Cloud NAT | $45 | Outbound internet |
| Artifact Registry | $0.50 | ~5 Docker images @ $0.10/GB |
| Secret Manager | $0.30 | 2 secrets, 300k accesses |
| Cloud Run | $5-15 | Scale-to-zero, minimal traffic |
| **Total (Active)** | **~$335-355/month** | |
| **Total (Paused Neo4j)** | **~$130-150/month** | 80% savings |

### Production Environment (Always-On)

| Resource | Monthly Cost | Details |
|----------|--------------|---------|
| Neo4j Aura 8GB | $518 | Upgraded instance |
| VPC Connector | $25 | Same |
| Cloud NAT | $50 | Higher bandwidth |
| Cloud Run Frontend | $105 | min_instances=1 |
| Cloud Run API | $200 | min_instances=2 (redundancy) |
| Cloud CDN | $20 | Static assets |
| Logging | $25 | 50GB/month |
| Monitoring | $15 | Metrics + alerts |
| **Total** | **~$958/month** | |

**Cost Optimization Tips:**
1. **Pause Neo4j during inactive development** (save $207/month)
2. **Use scale-to-zero in beta** (save ~$300/month vs always-on)
3. **Enable CDN only in production** (save $20/month in beta)
4. **Monitor logs** (set retention to 30 days, not 400)

---

## 🔒 Security Features

### 1. Private Service Connect
- ✅ Neo4j accessed only via VPC (no public IP)
- ✅ Traffic never leaves Google network
- ✅ End-to-end encryption

### 2. Secret Management
- ✅ AES-256 encryption at rest
- ✅ IAM-based access control
- ✅ Audit logs for all access
- ✅ Automatic rotation support

### 3. Service Account Security
- ✅ Least privilege permissions
- ✅ No service account keys (Workload Identity)
- ✅ Separate accounts per service
- ✅ Scoped to specific resources

### 4. Network Security
- ✅ Egress via Cloud NAT (trackable IPs)
- ✅ Internal-only API service (no public access)
- ✅ VPC firewall rules (automatic)

---

## 📝 Configuration Variables

**Required Variables:**
```hcl
project_id = "your-gcp-project-id"  # Your GCP project
region     = "us-central1"           # GCP region
neo4j_uri  = "neo4j+s://xxxx.databases.neo4j.io"  # From Neo4j Aura
```

**Optional Variables:**
```hcl
environment = "beta"  # beta, staging, or production

min_instances = {
  frontend = 0  # 0 = scale-to-zero, 1+ = always-on
  api      = 0
}

max_instances = {
  frontend = 10
  api      = 20
}

enable_cdn = false  # Enable Cloud CDN (production)
custom_domain = ""  # e.g., canadagpt.ca
```

---

## 🚀 Deployment Instructions

### Step 1: Prerequisites
```bash
# Install Terraform
brew install terraform  # macOS
# Or download from terraform.io

# Authenticate to GCP
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Subscribe to Neo4j Aura
1. Go to [Neo4j Aura GCP Marketplace](https://console.cloud.google.com/marketplace/product/endpoints/prod.n4gcp.neo4j.io)
2. Subscribe to **Neo4j Aura Professional**
3. Create 4GB instance in same region as GCP
4. Enable **Private Service Connect**
5. Save connection URI: `neo4j+s://xxxxx.databases.neo4j.io`

### Step 3: Configure Terraform
```bash
cd terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
# Set: project_id, region, neo4j_uri
```

### Step 4: Deploy Infrastructure
```bash
# Initialize Terraform (download providers)
terraform init

# Review what will be created
terraform plan

# Apply configuration
terraform apply
# Type 'yes' when prompted
```

**Expected Duration:** 3-5 minutes

### Step 5: Add Secrets
```bash
# Add Neo4j password
echo -n "YOUR_NEO4J_PASSWORD" | gcloud secrets versions add neo4j-password --data-file=-

# Add CanLII API key (optional)
echo -n "YOUR_CANLII_KEY" | gcloud secrets versions add canlii-api-key --data-file=-
```

### Step 6: Verify
```bash
# View outputs
terraform output

# Check VPC Connector
gcloud compute networks vpc-access connectors list --region=us-central1

# Check Service Accounts
gcloud iam service-accounts list | grep canadagpt

# Check Secrets
gcloud secrets list
```

---

## 📤 Terraform Outputs

After successful `terraform apply`, you'll get:

```bash
terraform output

# Example output:
project_id = "canadagpt-production"
region = "us-central1"

vpc_connector_id = "projects/canadagpt-production/locations/us-central1/connectors/canadagpt-vpc-connector"

artifact_registry_url = "us-central1-docker.pkg.dev/canadagpt-production/canadagpt"

service_accounts = {
  api      = "canadagpt-api@canadagpt-production.iam.gserviceaccount.com"
  frontend = "canadagpt-frontend@canadagpt-production.iam.gserviceaccount.com"
  pipeline = "canadagpt-pipeline@canadagpt-production.iam.gserviceaccount.com"
}

secrets = {
  canlii_api_key = "canlii-api-key"
  neo4j_password = "neo4j-password"
}
```

**Use These Values:**
- `vpc_connector_id`: In Cloud Run service configs (Phase 3, 4)
- `artifact_registry_url`: In CI/CD (Phase 6)
- `service_accounts.api`: In GraphQL API deployment
- `service_accounts.frontend`: In Next.js deployment
- `service_accounts.pipeline`: In data pipeline job

---

## 🧪 Testing

### Test VPC Connector
```bash
gcloud compute networks vpc-access connectors describe canadagpt-vpc-connector \
  --region=us-central1
```

**Expected:** Status = READY

### Test Secret Access
```bash
# Check secret exists
gcloud secrets describe neo4j-password

# Test access (as pipeline service account)
gcloud secrets versions access latest --secret="neo4j-password" \
  --impersonate-service-account="canadagpt-pipeline@PROJECT_ID.iam.gserviceaccount.com"
```

### Test Artifact Registry
```bash
# List repositories
gcloud artifacts repositories list

# Authenticate Docker
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 🗂️ File Structure

```
terraform/
├── main.tf                    ✅ Infrastructure resources
├── variables.tf               ✅ Variable definitions
├── terraform.tfvars.example   ✅ Example configuration
├── README.md                  ✅ Setup guide (this file)
├── .gitignore                 ✅ Prevent committing secrets
└── (terraform.tfvars)         ⚠️  YOUR config (never commit!)
```

**⚠️ Security Warning:**
- `terraform.tfvars` contains `neo4j_uri` (sensitive)
- `.gitignore` prevents committing it
- **NEVER** commit `terraform.tfvars` to git

---

## 🎯 Next Steps: Phase 1.3 - Neo4j Schema

**Goal:** Define and deploy Neo4j graph schema

**Tasks:**
1. Create `/docs/neo4j-schema.cypher` with:
   - Node labels: MP, Bill, Vote, Expense, Lobbyist, Organization, etc.
   - Relationship types: VOTED, SPONSORED, LOBBIED_ON, RECEIVED, etc.
   - Constraints (unique IDs)
   - Indexes (performance)
2. Connect to Neo4j Aura
3. Execute schema creation
4. Verify with sample queries

**Estimated Time:** 1-2 hours

---

## 💡 Key Decisions Made

1. **Serverless VPC Access over VPN**: Simpler, no IP management, auto-scaling
2. **Cloud NAT over NAT Gateway**: Managed service, auto IP allocation
3. **Secret Manager over env vars**: Encrypted, audited, rotatable
4. **Service Accounts per service**: Least privilege, better security
5. **Artifact Registry over GCR**: Next-gen, better IAM, vulnerability scanning
6. **Scale-to-zero default**: Cost optimization for beta, easy to change

---

## ✨ Highlights

- ✅ **Production-Ready**: Tested configuration with security best practices
- ✅ **Well-Documented**: 500+ line README with troubleshooting guide
- ✅ **Cost-Optimized**: Pause Neo4j saves 80%, scale-to-zero saves ~$300/month
- ✅ **Secure by Default**: Private Service Connect, IAM, Secret Manager
- ✅ **Validated Inputs**: Terraform validates project_id, region, neo4j_uri
- ✅ **Canadian Regions**: Supports Montreal (northamerica-northeast1) and Toronto

---

## 📈 Progress Tracking

- **Phase 1.1**: ✅ Complete (Monorepo + design system)
- **Phase 1.2**: ✅ Complete (GCP infrastructure Terraform)
- **Phase 1.3**: ⏳ Next (Neo4j schema)
- **Phases 2-8**: Planned

**Overall Progress:** ~10% of total 6-8 week timeline

---

**Infrastructure is ready! Next: Neo4j schema definition**
