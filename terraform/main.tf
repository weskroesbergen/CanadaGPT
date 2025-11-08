/**
 * CanadaGPT - Google Cloud Platform Infrastructure
 *
 * This Terraform configuration provisions all GCP resources for CanadaGPT:
 * - VPC networking with Serverless VPC Access Connector
 * - Cloud NAT for outbound traffic
 * - Service Accounts with IAM permissions
 * - Secret Manager for credentials
 * - Artifact Registry for Docker images
 * - Cloud Run services (frontend, API)
 * - Cloud Run Jobs (data pipeline)
 * - Cloud Scheduler (nightly sync)
 *
 * Prerequisites:
 * 1. GCP project created
 * 2. Billing enabled
 * 3. gcloud CLI authenticated: gcloud auth application-default login
 * 4. APIs enabled (see README.md)
 */

terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.10"
    }
  }

  # Optional: Use GCS backend for state management (recommended for production)
  # backend "gcs" {
  #   bucket = "canadagpt-terraform-state"
  #   prefix = "terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",              # Cloud Run
    "vpcaccess.googleapis.com",        # Serverless VPC Access
    "compute.googleapis.com",          # Compute Engine (for NAT, VPC)
    "artifactregistry.googleapis.com", # Artifact Registry
    "secretmanager.googleapis.com",    # Secret Manager
    "cloudbuild.googleapis.com",       # Cloud Build
    "cloudscheduler.googleapis.com",   # Cloud Scheduler
    "logging.googleapis.com",          # Cloud Logging
    "monitoring.googleapis.com",       # Cloud Monitoring
  ])

  service            = each.key
  disable_on_destroy = false
}

# ============================================
# VPC Network
# ============================================

resource "google_compute_network" "canadagpt_vpc" {
  name                    = "canadagpt-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.required_apis]
}

# Subnet for VPC Connector (required for Cloud Run to access VPC)
resource "google_compute_subnetwork" "vpc_connector_subnet" {
  name          = "canadagpt-connector-subnet"
  ip_cidr_range = "10.8.0.0/28" # /28 is required for VPC Connector
  region        = var.region
  network       = google_compute_network.canadagpt_vpc.id

  private_ip_google_access = true
}

# Serverless VPC Access Connector
# Required for Cloud Run services to connect to Neo4j via Private Service Connect
resource "google_vpc_access_connector" "canadagpt_connector" {
  name          = "canadagpt-vpc-connector"
  region        = var.region
  network       = google_compute_network.canadagpt_vpc.name
  ip_cidr_range = "10.8.0.0/28"

  min_instances = 2
  max_instances = 3

  machine_type = "e2-micro"

  depends_on = [
    google_compute_subnetwork.vpc_connector_subnet,
    google_project_service.required_apis
  ]
}

# Cloud Router (required for Cloud NAT)
resource "google_compute_router" "canadagpt_router" {
  name    = "canadagpt-router"
  region  = var.region
  network = google_compute_network.canadagpt_vpc.id
}

# Cloud NAT
# Provides outbound internet access for Cloud Run services (for government API calls)
resource "google_compute_router_nat" "canadagpt_nat" {
  name   = "canadagpt-nat"
  router = google_compute_router.canadagpt_router.name
  region = var.region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# ============================================
# Service Accounts
# ============================================

# Frontend Service Account
resource "google_service_account" "frontend_sa" {
  account_id   = "canadagpt-frontend"
  display_name = "CanadaGPT Frontend Service Account"
  description  = "Service account for Next.js frontend Cloud Run service"
}

# API Service Account
resource "google_service_account" "api_sa" {
  account_id   = "canadagpt-api"
  display_name = "CanadaGPT API Service Account"
  description  = "Service account for GraphQL API Cloud Run service"
}

# Data Pipeline Service Account
resource "google_service_account" "pipeline_sa" {
  account_id   = "canadagpt-pipeline"
  display_name = "CanadaGPT Data Pipeline Service Account"
  description  = "Service account for data pipeline Cloud Run Job"
}

# ============================================
# Secret Manager
# ============================================

# Neo4j Password
resource "google_secret_manager_secret" "neo4j_password" {
  secret_id = "neo4j-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# CanLII API Key (optional - user provides)
resource "google_secret_manager_secret" "canlii_api_key" {
  secret_id = "canlii-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# IAM bindings for secrets
# API service account needs access to Neo4j password
resource "google_secret_manager_secret_iam_member" "api_neo4j_access" {
  secret_id = google_secret_manager_secret.neo4j_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_sa.email}"
}

# Pipeline service account needs access to both secrets
resource "google_secret_manager_secret_iam_member" "pipeline_neo4j_access" {
  secret_id = google_secret_manager_secret.neo4j_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "pipeline_canlii_access" {
  secret_id = google_secret_manager_secret.canlii_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# ============================================
# Artifact Registry
# ============================================

resource "google_artifact_registry_repository" "canadagpt_repo" {
  location      = var.region
  repository_id = "canadagpt"
  description   = "Docker images for CanadaGPT services"
  format        = "DOCKER"

  depends_on = [google_project_service.required_apis]
}

# Grant service accounts access to pull images
resource "google_artifact_registry_repository_iam_member" "frontend_pull" {
  location   = google_artifact_registry_repository.canadagpt_repo.location
  repository = google_artifact_registry_repository.canadagpt_repo.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.frontend_sa.email}"
}

resource "google_artifact_registry_repository_iam_member" "api_pull" {
  location   = google_artifact_registry_repository.canadagpt_repo.location
  repository = google_artifact_registry_repository.canadagpt_repo.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_artifact_registry_repository_iam_member" "pipeline_pull" {
  location   = google_artifact_registry_repository.canadagpt_repo.location
  repository = google_artifact_registry_repository.canadagpt_repo.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# ============================================
# Outputs
# ============================================

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

output "vpc_connector_id" {
  description = "VPC Connector ID (use in Cloud Run services)"
  value       = google_vpc_access_connector.canadagpt_connector.id
}

output "artifact_registry_url" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.canadagpt_repo.repository_id}"
}

output "service_accounts" {
  description = "Service account emails"
  value = {
    frontend = google_service_account.frontend_sa.email
    api      = google_service_account.api_sa.email
    pipeline = google_service_account.pipeline_sa.email
  }
}

output "secrets" {
  description = "Secret Manager secret names"
  value = {
    neo4j_password  = google_secret_manager_secret.neo4j_password.secret_id
    canlii_api_key  = google_secret_manager_secret.canlii_api_key.secret_id
  }
}
