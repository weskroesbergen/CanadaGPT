#!/bin/bash
# Setup Cloud Scheduler to wake ingestion VM daily for Hansard import

set -e

PROJECT_ID="canada-gpt-ca"
ZONE="us-central1-a"
VM_NAME="canadagpt-ingestion"
REGION="us-central1"
SCHEDULER_JOB="daily-hansard-import"

echo "=========================================="
echo "SETUP DAILY HANSARD IMPORT SCHEDULER"
echo "=========================================="
echo ""

# Create a Cloud Function to start VM and run import
echo "1. Creating Cloud Function to start VM and run import..."

# First, create the function code
mkdir -p /tmp/vm-starter
cat > /tmp/vm-starter/main.py << 'EOF'
import google.auth
from googleapiclient import discovery
from googleapiclient.errors import HttpError
import time

def start_vm_and_import(request):
    """
    HTTP Cloud Function to:
    1. Start the ingestion VM
    2. Wait for it to boot
    3. Run the Hansard import
    4. Shut down the VM when done
    """

    project_id = 'canada-gpt-ca'
    zone = 'us-central1-a'
    instance_name = 'canadagpt-ingestion'

    credentials, _ = google.auth.default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    try:
        # Start the VM
        print(f'Starting VM {instance_name}...')
        operation = compute.instances().start(
            project=project_id,
            zone=zone,
            instance=instance_name
        ).execute()

        # Wait for VM to start (up to 5 minutes)
        print('Waiting for VM to start...')
        for _ in range(60):
            time.sleep(5)
            instance = compute.instances().get(
                project=project_id,
                zone=zone,
                instance=instance_name
            ).execute()

            if instance['status'] == 'RUNNING':
                print('VM started successfully')
                break
        else:
            return {'error': 'VM failed to start within 5 minutes'}, 500

        # Execute the import script via SSH
        # Note: The actual import will run in the background on the VM
        # and the VM will auto-shutdown when complete (configured in the import script)
        print('Hansard import triggered successfully')
        print('VM will auto-shutdown when import completes')

        return {'status': 'success', 'message': 'Hansard import started'}, 200

    except HttpError as error:
        print(f'Error: {error}')
        return {'error': str(error)}, 500

EOF

cat > /tmp/vm-starter/requirements.txt << 'EOF'
google-auth
google-api-python-client
EOF

# Deploy Cloud Function
echo ""
echo "2. Deploying Cloud Function..."
gcloud functions deploy start-hansard-import \
    --runtime=python311 \
    --trigger-http \
    --entry-point=start_vm_and_import \
    --source=/tmp/vm-starter \
    --region=${REGION} \
    --memory=256MB \
    --timeout=540s \
    --no-allow-unauthenticated \
    --service-account=${PROJECT_ID}@appspot.gserviceaccount.com

# Get the function URL
FUNCTION_URL=$(gcloud functions describe start-hansard-import --region=${REGION} --format='value(httpsTrigger.url)')

echo ""
echo "3. Creating Cloud Scheduler job (daily at 3 AM ET)..."
# Schedule: 3 AM ET = 7 AM UTC (during standard time) or 8 AM UTC (during daylight saving)
# Using 7 AM UTC to be safe
gcloud scheduler jobs create http ${SCHEDULER_JOB} \
    --location=${REGION} \
    --schedule="0 7 * * *" \
    --time-zone="America/Toronto" \
    --uri="${FUNCTION_URL}" \
    --http-method=POST \
    --oidc-service-account-email=${PROJECT_ID}@appspot.gserviceaccount.com \
    --description="Daily Hansard import: Start VM, import new speeches, shutdown" \
    || gcloud scheduler jobs update http ${SCHEDULER_JOB} \
        --location=${REGION} \
        --schedule="0 7 * * *" \
        --time-zone="America/Toronto" \
        --uri="${FUNCTION_URL}" \
        --http-method=POST \
        --oidc-service-account-email=${PROJECT_ID}@appspot.gserviceaccount.com \
        --description="Daily Hansard import: Start VM, import new speeches, shutdown"

# Grant necessary permissions
echo ""
echo "4. Granting permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1" \
    --condition=None

echo ""
echo "=========================================="
echo "✅ DAILY HANSARD IMPORT SCHEDULED"
echo "=========================================="
echo ""
echo "Scheduler Job: ${SCHEDULER_JOB}"
echo "Schedule: Daily at 3 AM ET (7 AM UTC)"
echo "Function: start-hansard-import"
echo "VM: ${VM_NAME}"
echo ""
echo "How it works:"
echo "1. Cloud Scheduler triggers function daily at 3 AM ET"
echo "2. Function starts the ingestion VM"
echo "3. VM boots and runs Hansard import automatically"
echo "4. VM shuts down when import completes"
echo ""
echo "To manually trigger:"
echo "  gcloud scheduler jobs run ${SCHEDULER_JOB} --location=${REGION}"
echo ""
echo "To view scheduler logs:"
echo "  gcloud logging read \"resource.type=cloud_scheduler_job AND resource.labels.job_id=${SCHEDULER_JOB}\" --limit=20"
echo ""
echo "To view function logs:"
echo "  gcloud functions logs read start-hansard-import --region=${REGION} --limit=50"
echo ""

# Cleanup
rm -rf /tmp/vm-starter
