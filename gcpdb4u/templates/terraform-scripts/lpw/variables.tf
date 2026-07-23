# ------------------------------------------------------------------
# All input variables for the lpw-demo3 root module.
# Values are supplied via *.auto.tfvars (workspace.auto.tfvars, providers.auto.tfvars).
# ------------------------------------------------------------------

# Databricks account
variable "databricks_account_id" {}
variable "databricks_account_console_url" {}
variable "databricks_admin_user" {}

# Workspace
variable "databricks_workspace_name" {}
variable "expected_workspace_status" {}

# GCP project / network
variable "google_project_id" {}
variable "google_project_number" {}
variable "google_region" {}
variable "google_vpc_id" {}
variable "create_vpc" {
  type        = bool
  default     = true # true = create the VPC (non-shared only); false = use existing
  description = "Create the VPC if it does not exist. Not supported with Shared VPC."
}
variable "workspace_subnet" {}
variable "workspace_subnet_cidr" {} # e.g. 10.1.0.0/26
variable "google_shared_vpc_project" {
  type        = string
  default     = "" # empty = non-shared VPC (default): VPC lives in google_project_id
  description = "Shared VPC host project. Leave empty for the default non-shared setup (VPC in google_project_id)."
}

# Workspace group assignments. Map of EXISTING account-group name => permission
# ("ADMIN" | "USER"). Groups/users/GSAs are managed out of band (see identities/);
# this only grants already-existing groups a role on THIS workspace. Empty = none.
variable "workspace_groups" {
  type        = map(string)
  default     = {}
  description = "Existing account groups to assign to this workspace: { group_name = \"ADMIN\"|\"USER\" }."
  validation {
    condition     = alltrue([for p in values(var.workspace_groups) : contains(["ADMIN", "USER"], p)])
    error_message = "Each workspace_groups value must be ADMIN or USER."
  }
}

# Workspace IP access lists (optional, default OFF). Two-step: (1) enable the
# feature on the workspace, (2) add the allow/block entries. When false, neither
# happens. The IP/CIDR entries live in ip_access_list.yaml (edit there).
variable "enable_ip_access_list" {
  type        = bool
  default     = false # false = no IP ACLs enabled on the workspace
  description = "Enable IP access lists on the workspace and apply the entries from ip_access_list.yaml. Default false."
}

# Unity Catalog metastore binding (optional). Bind THIS workspace to an EXISTING
# regional metastore (one per region per account). The metastore is created out of
# band (see metastore/), not here. Two ways to identify it:
#   - metastore_name : friendly; resolved to an ID via the databricks_metastores
#                      data source (name -> id map). Preferred.
#   - metastore_id   : explicit ID; overrides the name lookup if both are set.
# Leave BOTH empty to skip UC binding entirely.
variable "metastore_name" {
  type        = string
  default     = ""
  description = "Name of an existing metastore to bind this workspace to (resolved to an ID). Must be the metastore for the workspace's region."
}
variable "metastore_id" {
  type        = string
  default     = ""
  description = "Explicit metastore ID. Optional override; takes precedence over metastore_name when set."
}

# Network Connectivity Config (NCC). Attached to the workspace only at RUNNING.
variable "enable_ncc" {
  type        = bool
  default     = true # true = create + attach NCC (at RUNNING)
  description = "Create a Network Connectivity Config and attach it to the workspace (stable egress / private connectivity for serverless). Attached only at RUNNING."
}

# Private Access Settings (PSC). Attached to the workspace only at RUNNING.
# PAS shape defaults to the LPW-safe posture (public access ENABLED, ACCOUNT level)
# via the public_access_enabled / private_access_level vars below.
variable "enable_private_access" {
  type        = bool
  default     = true # true = build full PSC path (endpoints, DNS, VPC endpoints, PAS)
  description = "Create a Private Access Settings object and attach it to the workspace."
}

# PAS shape. Defaults are the LPW-safe posture (hybrid: public ON, ACCOUNT level).
# Overridable, but flipping public_access_enabled = false with no working PSC
# endpoints registered will lock you out of the workspace — change deliberately.
variable "public_access_enabled" {
  type        = bool
  default     = true # LPW default: public access ENABLED (hybrid with PSC)
  description = "PAS public access. true = hybrid (public + PSC); false = PSC-only (lockout risk if endpoints not working)."
}
variable "private_access_level" {
  type        = string
  default     = "ACCOUNT" # LPW default: any endpoint registered in the account
  description = "PAS private access level: ACCOUNT (any account-registered endpoint) or ENDPOINT (only allowed_vpc_endpoint_ids)."
  validation {
    condition     = contains(["ACCOUNT", "ENDPOINT"], var.private_access_level)
    error_message = "private_access_level must be ACCOUNT or ENDPOINT."
  }
}

# PSC endpoint plumbing (only used when enable_private_access = true).
variable "psc_subnet_cidr" {
  type        = string
  default     = "10.1.255.0/26" # separate from workspace_subnet_cidr; hosts the 2 PSC IPs
  description = "CIDR for the dedicated PSC endpoint subnet."
}

# Databricks service attachment URIs. Defaults are us-central1.
# Source: https://docs.databricks.com/gcp/en/resources/ip-domain-region#psc
variable "workspace_service_attachment" {
  type        = string
  default     = "projects/gcp-prod-general/regions/us-central1/serviceAttachments/plproxy-psc-endpoint-all-ports"
  description = "Databricks workspace (plproxy) PSC service attachment URI for the region."
}
variable "relay_service_attachment" {
  type        = string
  default     = "projects/prod-gcp-us-central1/regions/us-central1/serviceAttachments/ngrok-psc-endpoint"
  description = "Databricks SCC relay (ngrok) PSC service attachment URI for the region."
}

# Auth
variable "google_service_account_email" {}
