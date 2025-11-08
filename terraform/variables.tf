/**
 * Terraform Variables for CanadaGPT Infrastructure
 */

variable "project_id" {
  description = "GCP Project ID"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Project ID must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"

  validation {
    condition = contains([
      "us-central1",
      "us-east1",
      "us-west1",
      "northamerica-northeast1", # Montreal
      "northamerica-northeast2", # Toronto
    ], var.region)
    error_message = "Region must be a valid GCP region. Recommended: us-central1 (Iowa) or northamerica-northeast1 (Montreal)."
  }
}

variable "environment" {
  description = "Environment name (beta, staging, production)"
  type        = string
  default     = "beta"

  validation {
    condition     = contains(["beta", "staging", "production"], var.environment)
    error_message = "Environment must be one of: beta, staging, production."
  }
}

variable "neo4j_uri" {
  description = "Neo4j Aura connection URI (e.g., neo4j+s://xxxxx.databases.neo4j.io)"
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^neo4j\\+s://", var.neo4j_uri))
    error_message = "Neo4j URI must start with 'neo4j+s://' for secure connection."
  }
}

variable "enable_cdn" {
  description = "Enable Cloud CDN for frontend (recommended for production)"
  type        = bool
  default     = false
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances (0 for scale-to-zero, 1+ for always-on)"
  type = object({
    frontend = number
    api      = number
  })

  default = {
    frontend = 0 # Beta: scale-to-zero
    api      = 0 # Beta: scale-to-zero
  }

  validation {
    condition     = var.min_instances.frontend >= 0 && var.min_instances.api >= 0
    error_message = "Minimum instances must be >= 0."
  }
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type = object({
    frontend = number
    api      = number
  })

  default = {
    frontend = 10
    api      = 20
  }
}

variable "custom_domain" {
  description = "Custom domain for frontend (e.g., canadagpt.ca)"
  type        = string
  default     = ""
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    project     = "canadagpt"
    managed_by  = "terraform"
    environment = "beta"
  }
}
