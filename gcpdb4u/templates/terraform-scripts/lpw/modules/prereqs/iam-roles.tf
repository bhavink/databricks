# ------------------------------------------------------------------
# Custom project IAM roles for the Databricks LPW workspace.
# The role bindings in the root (iam-grants.tf) reference these by ID via the
# outputs below, which also forces Terraform to create the roles first.
# ------------------------------------------------------------------

resource "google_project_iam_custom_role" "lpw_project_role" {
  role_id     = "lpw.databricks.project.role.v2"
  title       = "LPW Databricks Project Role v2"
  description = "Provides read access to project-wide resources for Databricks LPW"
  project     = var.google_project_id
  stage       = "GA"
  permissions = [
    "compute.disks.list",
    "compute.globalOperations.list",
    "compute.instances.list",
    # Beta permission; used by an upcoming API to steer clusters toward the
    # zone with best available capacity.
    "compute.instances.recommendLocations",
    "compute.regionOperations.list",
    "compute.regions.get",
    "compute.reservations.get",
    "compute.reservations.list",
    "compute.spotAssistants.get",
    "compute.zoneOperations.list",
    "compute.zones.get",
    "compute.zones.list",
    "iam.serviceAccounts.actAs",
    "resourcemanager.projects.get",
    "serviceusage.quotas.get",
    "serviceusage.services.list",
    "storage.buckets.list",
  ]
}

resource "google_project_iam_custom_role" "lpw_resource_role" {
  role_id     = "lpw.databricks.resource.role.v2"
  title       = "LPW Databricks Resource Role v2"
  description = "Manage compute resources and GCS for LPW"
  project     = var.google_project_id
  stage       = "GA"
  permissions = [
    "compute.disks.create",
    "compute.disks.delete",
    "compute.disks.get",
    "compute.disks.resize",
    "compute.disks.setLabels",
    "compute.disks.update",
    "compute.disks.use",
    "compute.disks.useReadOnly",
    "compute.instances.attachDisk",
    "compute.instances.create",
    "compute.instances.delete",
    "compute.instances.detachDisk",
    "compute.instances.get",
    "compute.instances.getGuestAttributes",
    "compute.instances.getSerialPortOutput",
    "compute.instances.setLabels",
    "compute.instances.setMetadata",
    "compute.instances.setServiceAccount",
    "compute.instances.setTags",
    "compute.instances.update",
    "storage.buckets.create",
    "storage.buckets.delete",
    "storage.buckets.get",
    "storage.buckets.getIamPolicy",
    "storage.buckets.setIamPolicy",
    "storage.buckets.update",
    "storage.multipartUploads.abort",
    "storage.multipartUploads.create",
    "storage.multipartUploads.list",
    "storage.multipartUploads.listParts",
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.update",
  ]
}

resource "google_project_iam_custom_role" "lpw_network_role" {
  role_id     = "lpw.databricks.network.role.v2"
  title       = "LPW Databricks Network Role v2"
  description = "Access to use and get subnetworks"
  project     = var.google_project_id
  stage       = "GA"
  permissions = [
    "compute.subnetworks.get",
    "compute.subnetworks.use",
  ]
}

# Fully-qualified role IDs (projects/<project>/roles/<role_id>), consumed by the
# root role bindings so grants order after role creation.
output "project_role_id" {
  value = google_project_iam_custom_role.lpw_project_role.id
}

output "resource_role_id" {
  value = google_project_iam_custom_role.lpw_resource_role.id
}

output "network_role_id" {
  value = google_project_iam_custom_role.lpw_network_role.id
}

# NOTE: the identity that RUNS Terraform (the deployer GSA) is NOT granted here.
# It gets PREDEFINED roles via prereqs.sh (custom roles can't grant the PSC/DNS
# perms the deploy needs). See PREREQUISITES.md. The 3 roles above are the
# least-privilege roles for the workspace COMPUTE SA — a different identity.
