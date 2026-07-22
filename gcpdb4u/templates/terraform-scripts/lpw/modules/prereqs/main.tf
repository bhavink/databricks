# Prereq module: CMK primitives that can be created BEFORE the Databricks
# workspace exists (they have no dependency on the workspace GSA).
#
# Stage 1:  terraform apply -target=module.prereqs
# Stage 2+: terraform apply   (workspace + workspace-SA IAM grants in root)
#
# NOT in this module (they depend on databricks_mws_workspaces.gcp_workspace_sa,
# which only exists after the workspace is created): the CMK workspace-SA grant
# and the project/resource/network IAM role assignments. Those stay in the root.

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
}

variable "google_project_id" {
  type        = string
  description = "GCP project ID."
}

variable "google_project_number" {
  type        = string
  description = "GCP project number (for GCP-managed service agent emails)."
}

variable "google_region" {
  type        = string
  description = "KMS key ring location."
}

variable "name_suffix" {
  type        = string
  description = "Random suffix shared with workspace/network naming (from root random_string)."
}

resource "google_kms_key_ring" "databricks_keyring" {
  project  = var.google_project_id
  name     = "databricks-keyring-${var.name_suffix}"
  location = var.google_region
}

resource "google_kms_crypto_key" "databricks_cmek" {
  name     = "databricks-cmek-${var.name_suffix}"
  key_ring = google_kms_key_ring.databricks_keyring.id
  purpose  = "ENCRYPT_DECRYPT"
}

# Grant cryptoKeyEncrypterDecrypter to the GCP-managed service agents
# (Compute Engine system SA and Cloud Storage service account).
resource "google_kms_crypto_key_iam_member" "databricks_cmek_gcp_service_agents" {
  for_each = toset([
    "serviceAccount:service-${var.google_project_number}@compute-system.iam.gserviceaccount.com",
    "serviceAccount:service-${var.google_project_number}@gs-project-accounts.iam.gserviceaccount.com",
  ])

  crypto_key_id = google_kms_crypto_key.databricks_cmek.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = each.value
}

output "crypto_key_id" {
  description = "Full resource ID of the CMK crypto key."
  value       = google_kms_crypto_key.databricks_cmek.id
}

output "key_ring_id" {
  value = google_kms_key_ring.databricks_keyring.id
}
