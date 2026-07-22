# ------------------------------------------------------------------
# Prereqs: everything that can be created before the workspace lives in
# module.prereqs (CMK, custom roles, network/subnet, compute SA, PSC endpoints).
# They can be applied first:
#   Stage 1:  terraform apply -target=module.prereqs
#   Stage 2+: terraform apply
# The post-workspace CMK grant below stays in the root (needs the workspace GSA).
# ------------------------------------------------------------------
locals {
  # VPC host project. Non-shared VPC (default): the workspace project itself.
  # Shared VPC: the host project supplied via google_shared_vpc_project.
  vpc_project_id = var.google_shared_vpc_project != "" ? var.google_shared_vpc_project : var.google_project_id

  # Guard: creating a VPC in a Shared VPC host project is out of scope here
  # (the host VPC is owned/managed by the host project, not this config).
  _assert_no_create_vpc_with_shared = (
    var.create_vpc && var.google_shared_vpc_project != ""
  ) ? tobool("create_vpc = true is not supported with Shared VPC (google_shared_vpc_project set)") : true
}

module "prereqs" {
  source = "./modules/prereqs"

  google_project_id     = var.google_project_id
  google_project_number = var.google_project_number
  google_region         = var.google_region
  name_suffix           = random_string.databricks_suffix.result

  # Subnet + firewall are created in the VPC host project (same as the workspace
  # project for non-shared VPC; the host project for shared VPC).
  vpc_project_id = local.vpc_project_id
  create_vpc     = var.create_vpc
  google_vpc_id  = var.google_vpc_id
  subnet_name    = var.workspace_subnet
  subnet_cidr    = var.workspace_subnet_cidr

  # PSC prereqs (subnet + endpoints). No-ops when enable_private_access = false.
  enable_private_access        = var.enable_private_access
  psc_subnet_cidr              = var.psc_subnet_cidr
  workspace_service_attachment = var.workspace_service_attachment
  relay_service_attachment     = var.relay_service_attachment
}

# Post-workspace grant: references the workspace GSA, so it waits on the same
# propagation sleep as the other GSA grants (see iam-grants.tf) — otherwise it can
# 400 "service account does not exist" against the just-created SA.
resource "google_kms_crypto_key_iam_member" "databricks_cmek_workspace_sa" {
  depends_on    = [time_sleep.wait_for_workspace_gsa]
  crypto_key_id = module.prereqs.crypto_key_id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${databricks_mws_workspaces.databricks_workspace.gcp_workspace_sa}"
}
