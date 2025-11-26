#!/bin/bash
set -e

# Deploy committee meeting importer Cloud Run job
# This job runs daily at 6am to check for and import new committee meetings

PROJECT_ID="canada-gpt-ca"
REGION="us-central1"
JOB_NAME="committee-daily-import"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}"

echo "================================================================================"
echo "DEPLOYING COMMITTEE MEETING DAILY IMPORT JOB"
echo "================================================================================"

# Get Neo4j password from Secret Manager
echo "Fetching Neo4j password from Secret Manager..."
NEO4J_PASSWORD=$(gcloud secrets versions access latest --secret="neo4j-password" --project="${PROJECT_ID}")

# Build and push Docker image using Cloud Build
echo "Building Docker image with Cloud Build..."
gcloud builds submit \
  --config=cloudbuild-committee.yaml \
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
    --vpc-connector=canadagpt-vpc-connector \
    --vpc-egress=private-ranges-only \
    --max-retries=2 \
    --task-timeout=30m \
    --memory=2Gi \
    --cpu=1 \
    --project=${PROJECT_ID}
else
  echo "Creating new Cloud Run job..."
  gcloud run jobs create ${JOB_NAME} \
    --region=${REGION} \
    --image=${IMAGE_NAME}:latest \
    --set-env-vars="NEO4J_URI=bolt://10.128.0.3:7687,NEO4J_USERNAME=neo4j" \
    --set-secrets="NEO4J_PASSWORD=neo4j-password:latest" \
    --vpc-connector=canadagpt-vpc-connector \
    --vpc-egress=private-ranges-only \
    --max-retries=2 \
    --task-timeout=30m \
    --memory=2Gi \
    --cpu=1 \
    --project=${PROJECT_ID}
fi

echo "✓ Cloud Run job deployed successfully"

# Create or update Cloud Scheduler job to run daily at 6am Eastern Time
SCHEDULER_JOB_NAME="committee-daily-import-trigger"

echo "Setting up Cloud Scheduler..."

# Check if scheduler job exists
if gcloud scheduler jobs describe ${SCHEDULER_JOB_NAME} --location=${REGION} --project=${PROJECT_ID} &>/dev/null; then
  echo "Updating existing scheduler job..."
  gcloud scheduler jobs update http ${SCHEDULER_JOB_NAME} \
    --location=${REGION} \
    --schedule="0 6 * * *" \
    --time-zone="America/Toronto" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --project=${PROJECT_ID}
else
  echo "Creating new scheduler job..."
  gcloud scheduler jobs create http ${SCHEDULER_JOB_NAME} \
    --location=${REGION} \
    --schedule="0 6 * * *" \
    --time-zone="America/Toronto" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --project=${PROJECT_ID}
fi

echo "✓ Cloud Scheduler configured to run daily at 6:00 AM Eastern Time"

echo "================================================================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""
echo "Job Name: ${JOB_NAME}"
echo "Image: ${IMAGE_NAME}:latest"
echo "Schedule: Daily at 6:00 AM Eastern Time (2 hours after Hansard import)"
echo ""
echo "To manually trigger the job:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo ""
echo "To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}\" --limit=50 --format=json"
echo ""
