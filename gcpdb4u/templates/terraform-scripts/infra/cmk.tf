***REMOVED*** Create KMS Key Rings and Crypto Keys per subnet region if enable_cmk is true
resource "google_kms_key_ring" "databricks_keyring" {
  count = var.create_cmk_resources ? length(var.subnet_configs) : 0
  project = var.vpc_project_id
  name     = "databricks-keyring-${element(keys(var.subnet_configs), count.index)}"
  location = var.subnet_configs[element(keys(var.subnet_configs), count.index)].region
}

resource "google_kms_crypto_key" "databricks_cmek" {
  count = var.create_cmk_resources ? length(var.subnet_configs) : 0
  name     = "databricks-cmek-${element(keys(var.subnet_configs), count.index)}"
  key_ring = google_kms_key_ring.databricks_keyring[count.index].id
  purpose  = "ENCRYPT_DECRYPT"  ***REMOVED*** Use ENCRYPT_DECRYPT for encryption purpose
}
