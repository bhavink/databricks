// override defaults set in variables.tf

spokecidr        = "10.178.0.0/20"
no_public_ip     = true
rglocation       = "westus"
dbfs_prefix      = "dbfs"
workspace_prefix = "dbwbk"
uc_root_storage  = "ucrootstorage" // adls storage account name, no space or special characters
uc_ext_storage   = "ucextstorage1" // adls storage account name, no space or special characters
tags_owner       = "bhavin.kukadia@databricks.com"
tags_removeafter = "2025-12-31" // YYYY-MM-DD
tags_environment = "Testing"
