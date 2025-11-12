#!/bin/bash
set -e

# Configuration
PROJECT_ID="canada-gpt-ca"
REGION="us-central1"
SERVICE_NAME="canadagpt-graph-api"
IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/canadagpt/graph-api:latest"
NEO4J_INTERNAL_IP="10.128.0.3"
NEO4J_PASSWORD="canadagpt2024"

echo "========================================="
echo "Deploying CanadaGPT GraphQL API to Cloud Run"
echo "========================================="
echo ""
echo "Service: $SERVICE_NAME"
echo "Image: $IMAGE"
echo "Region: $REGION"
echo ""

# Step 1: Validate environment variables
echo "🔍 Step 1/4: Validating environment variables..."
export NEO4J_URI="bolt://${NEO4J_INTERNAL_IP}:7687"
export CORS_ORIGINS="https://canadagpt.ca;http://localhost:3000;https://www.canadagpt.ca"
./scripts/validate-env.sh graph-api production || {
  echo "❌ Environment validation failed. Fix errors above and try again."
  exit 1
}
echo ""

# Build and push Docker image with linux/amd64 platform for Cloud Run
echo "📦 Step 2/4: Building Docker image for linux/amd64 (no-cache to prevent stale code)..."
cd packages/graph-api
docker buildx build --platform linux/amd64 --no-cache -t $IMAGE --push .
cd ../..
echo ""

# Deploy to Cloud Run with Direct VPC Egress
echo "🚀 Step 3/4: Deploying to Cloud Run with authentication..."
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE \
  --platform=managed \
  --region=$REGION \
  --project=$PROJECT_ID \
  --allow-unauthenticated \
  --port=4000 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=300 \
  --set-env-vars="NEO4J_URI=bolt://${NEO4J_INTERNAL_IP}:7687,NEO4J_USER=neo4j,NODE_ENV=production,CORS_ORIGINS=https://canadagpt.ca;http://localhost:3000;https://www.canadagpt.ca,GRAPHQL_INTROSPECTION=false,GRAPHQL_PLAYGROUND=false,GRAPHIQL_ALLOWED_IPS=,AUTH_REQUIRED=true" \
  --set-secrets="NEO4J_PASSWORD=neo4j-password:latest,FRONTEND_API_KEY=canadagpt-frontend-api-key:latest,PUBLIC_API_KEY=canadagpt-public-api-key:latest,ADMIN_API_KEY=canadagpt-admin-api-key:latest,JWT_SECRET=canadagpt-jwt-secret:latest" \
  --service-account=canadagpt-graph-api-sa@canada-gpt-ca.iam.gserviceaccount.com \
  --vpc-connector=canadagpt-connector \
  --vpc-egress=private-ranges-only

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.url)")

echo ""
echo "📡 GraphQL API URL: $SERVICE_URL/graphql"
echo ""

# Step 4: Run smoke tests
echo "🧪 Step 4/4: Running smoke tests..."
./scripts/smoke-test.sh "$SERVICE_URL" "https://canadagpt.ca" || {
  echo ""
  echo "⚠️  Warning: Smoke tests failed. The deployment completed but may have issues."
  echo "   Review the errors above and test manually:"
  echo "   curl $SERVICE_URL/graphql?query={__typename}"
  exit 1
}

echo ""
echo "========================================="
echo "🎉 Deployment successful and verified!"
echo "========================================="
echo ""
