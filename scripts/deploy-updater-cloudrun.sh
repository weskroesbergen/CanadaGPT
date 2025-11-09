#!/bin/bash
# Deploy lightweight updater to Cloud Run as a scheduled job

set -e

PROJECT_ID="canada-gpt-ca"
REGION="us-central1"
SERVICE_NAME="canadagpt-updater"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "DEPLOYING LIGHTWEIGHT UPDATER TO CLOUD RUN"
echo "=========================================="
echo ""

# Navigate to repository root
cd "$(dirname "$0")/.."

# Build Docker image
echo "1. Building Docker image..."
docker build -f packages/data-pipeline/Dockerfile.updater -t ${IMAGE_NAME}:latest .

# Push to Google Container Registry
echo ""
echo "2. Pushing to GCR..."
docker push ${IMAGE_NAME}:latest

# Get Neo4j connection details
echo ""
echo "3. Getting Neo4j connection info..."
read -p "Neo4j URI (e.g., bolt://10.128.0.2:7687): " NEO4J_URI
read -p "Neo4j Username [neo4j]: " NEO4J_USER
NEO4J_USER=${NEO4J_USER:-neo4j}
read -sp "Neo4j Password: " NEO4J_PASSWORD
echo ""

# Deploy to Cloud Run as a job
echo ""
echo "4. Deploying Cloud Run job..."
gcloud run jobs create ${SERVICE_NAME} \
    --image=${IMAGE_NAME}:latest \
    --region=${REGION} \
    --memory=512Mi \
    --cpu=1 \
    --max-retries=2 \
    --task-timeout=10m \
    --set-env-vars="NEO4J_URI=${NEO4J_URI},NEO4J_USER=${NEO4J_USER},NEO4J_PASSWORD=${NEO4J_PASSWORD}" \
    --vpc-connector=canadagpt-connector \
    --vpc-egress=private-ranges-only \
    || gcloud run jobs update ${SERVICE_NAME} \
        --image=${IMAGE_NAME}:latest \
        --region=${REGION} \
        --memory=512Mi \
        --cpu=1 \
        --max-retries=2 \
        --task-timeout=10m \
        --set-env-vars="NEO4J_URI=${NEO4J_URI},NEO4J_USER=${NEO4J_USER},NEO4J_PASSWORD=${NEO4J_PASSWORD}" \
        --vpc-connector=canadagpt-connector \
        --vpc-egress=private-ranges-only

# Create Cloud Scheduler job to run hourly
echo ""
echo "5. Creating Cloud Scheduler job (runs hourly)..."
gcloud scheduler jobs create http ${SERVICE_NAME}-schedule \
    --location=${REGION} \
    --schedule="0 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${SERVICE_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email=${PROJECT_ID}@appspot.gserviceaccount.com \
    --description="Run lightweight parliamentary data updates hourly" \
    || gcloud scheduler jobs update http ${SERVICE_NAME}-schedule \
        --location=${REGION} \
        --schedule="0 * * * *" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${SERVICE_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email=${PROJECT_ID}@appspot.gserviceaccount.com \
        --description="Run lightweight parliamentary data updates hourly"

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Cloud Run Job: ${SERVICE_NAME}"
echo "Schedule: Every hour (0 * * * *)"
echo "Memory: 512Mi"
echo "Timeout: 10 minutes"
echo ""
echo "To manually trigger:"
echo "  gcloud run jobs execute ${SERVICE_NAME} --region=${REGION}"
echo ""
echo "To view logs:"
echo "  gcloud run jobs executions list --job=${SERVICE_NAME} --region=${REGION}"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${SERVICE_NAME}\" --limit=50"
echo ""
