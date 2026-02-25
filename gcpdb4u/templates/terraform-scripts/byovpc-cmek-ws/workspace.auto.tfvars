databricks_account_id          = "<databricks_account_id>"             #prod
databricks_account_console_url = "https://accounts.gcp.databricks.com" #prod

databricks_workspace_name = "labs-psc-ws1"
databricks_admin_user     = "user@dcompany.com"

google_vpc_id = "databricks-vpc-xpn"
node_subnet   = "node-subnet"

# if you are bringing pre-created key then uncomment the following line and update it with your key resource id
# for more details on customer managed keys please refer to https://docs.gcp.databricks.com/security/keys/customer-managed-keys.html
# we will be using same key for managed and unmanaged services encryption.

# cmek_resource_id = "projects/<gcp_project>/locations/<gcp_region>/keyRings/<keyring_name>/cryptoKeys/<key_name>"
