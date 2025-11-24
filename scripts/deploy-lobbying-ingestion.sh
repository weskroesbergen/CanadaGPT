#!/bin/bash
set -e

# Deploy lobbying data ingestion Cloud Run job
# This job runs weekly to refresh lobbying registry data

PROJECT_ID="canada-gpt-ca"
REGION="us-central1"
JOB_NAME="lobbying-ingestion"
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/canadagpt/${JOB_NAME}"

echo "================================================================================"
echo "DEPLOYING LOBBYING DATA INGESTION JOB"
echo "================================================================================"

# Get Neo4j password from Secret Manager
echo "Fetching Neo4j password from Secret Manager..."
NEO4J_PASSWORD=$(gcloud secrets versions access latest --secret="neo4j-password" --project="${PROJECT_ID}")

# Build and push Docker image using Cloud Build
echo "Building Docker image with Cloud Build..."
gcloud builds submit \
  --config=packages/data-pipeline/cloudbuild-lobbying-ingestion.yaml \
  --project=${PROJECT_ID} \
  .

# Check if job exists
if gcloud run jobs describe ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID} &>/dev/null; then
  echo "Updating existing Cloud Run job..."
  gcloud run jobs update ${JOB_NAME} \
    --region=${REGION} \
    --image=${IMAGE_NAME}:latest \
    --set-env-vars="NEO4J_URI=bolt://10.128.0.3:7687,NEO4J_USERNAME=neo4j" \
    --set-secrets="NEO4J_PASSWORD=neo4j-password:latest" \
    --vpc-connector=canadagpt-connector \
    --vpc-egress=private-ranges-only \
    --max-retries=1 \
    --task-timeout=120m \
    --memory=4Gi \
    --cpu=2 \
    --project=${PROJECT_ID}
else
  echo "Creating new Cloud Run job..."
  gcloud run jobs create ${JOB_NAME} \
    --region=${REGION} \
    --image=${IMAGE_NAME}:latest \
    --set-env-vars="NEO4J_URI=bolt://10.128.0.3:7687,NEO4J_USERNAME=neo4j" \
    --set-secrets="NEO4J_PASSWORD=neo4j-password:latest" \
    --vpc-connector=canadagpt-connector \
    --vpc-egress=private-ranges-only \
    --max-retries=1 \
    --task-timeout=120m \
    --memory=4Gi \
    --cpu=2 \
    --project=${PROJECT_ID}
fi

echo "✓ Cloud Run job deployed successfully"

# Create or update Cloud Scheduler job to run weekly on Sundays at 2am UTC
SCHEDULER_JOB_NAME="lobbying-ingestion-trigger"

echo "Setting up Cloud Scheduler..."

# Check if scheduler job exists
if gcloud scheduler jobs describe ${SCHEDULER_JOB_NAME} --location=${REGION} --project=${PROJECT_ID} &>/dev/null; then
  echo "Updating existing scheduler job..."
  gcloud scheduler jobs update http ${SCHEDULER_JOB_NAME} \
    --location=${REGION} \
    --schedule="0 2 * * 0" \
    --time-zone="UTC" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --project=${PROJECT_ID}
else
  echo "Creating new scheduler job..."
  gcloud scheduler jobs create http ${SCHEDULER_JOB_NAME} \
    --location=${REGION} \
    --schedule="0 2 * * 0" \
    --time-zone="UTC" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --project=${PROJECT_ID}
fi

echo "✓ Cloud Scheduler configured to run weekly on Sundays at 2:00 AM UTC"

echo "================================================================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""
echo "Job Name: ${JOB_NAME}"
echo "Image: ${IMAGE_NAME}:latest"
echo "Schedule: Weekly on Sundays at 2:00 AM UTC"
echo ""
echo "To manually trigger the job:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo ""
echo "To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}\" --limit=50 --format=json"
echo ""
