## Goal

Create Databricks workspace using Terraform & Service Account based authentication and impersonation.
This documentation outlines the steps to create and configure two Google Cloud Platform (GCP) service accounts, namely `caller-sa` and `privileged-sa`. The caller-sa service account is granted the "Service Account Token Creator" role, while the privileged-sa service account is given the required [permissions](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/permissions.html#required-permissions-for-the-workspace-creator) to create a Databricks workspace. Please note that databricks terraform provider only support GCP Service Account based authentication. 

## Create two service accounts

- **caller-sa:** Low privileged sa, used to impersonate privileged sa.
- **privileged-sa:** Used to create databricks and gcp resources.

## Assign roles/permissions to service accounts

- **privileged-sa:** Required [permissions](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/permissions.html#required-permissions-for-the-workspace-creator) to create a workspace and if you are using shared VPC then grant `Network` viewer role on the host or shared VPC project.
- **caller-sa:** [Service Account Token Creator](https://cloud.google.com/iam/docs/understanding-roles#iam.serviceAccountTokenCreator) role on the caller-sa.

Make sure to replace following variables with actual values while running the commands.

- YOUR_PROJECT_ID: Replace with your actual GCP project ID.
- /path/to/caller-sa-key.json: Replace with the desired local path and filename for the downloaded key file.

### Create the service account

`gcloud iam service-accounts create caller-sa --display-name="Caller Service Account"`

### Grant the service account the "Service Account Token Creator" role
`gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:caller-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountTokenCreator"`

### Create the service account
`gcloud iam service-accounts create privileged-sa --display-name="Privileged Service Account"`

### Create a custom role for Databricks Admin
gcloud iam roles create DatabricksAdmin --project=YOUR_PROJECT_ID --file=databricks-admin-role.yaml

### Create the YAML file for the custom role
```
cat << EOF > databricks-admin-role.yaml
title: "Databricks Admin"
description: "Custom role with permissions required for Databricks workspace creation"
stage: "GA"
includedPermissions:
- iam.roles.get
- iam.roles.create
- iam.roles.delete
- iam.roles.update
- iam.serviceAccounts.getIamPolicy
- iam.serviceAccounts.setIamPolicy
- resourcemanager.projects.get
- resourcemanager.projects.getIamPolicy
- resourcemanager.projects.setIamPolicy
- serviceusage.services.enable
- serviceusage.services.get
- serviceusage.services.list
- compute.networks.get
- compute.subnetworks.get
- compute.projects.get
- compute.forwardingRules.get
- compute.forwardingRules.list
EOF
```
### Verify the role creation
`gcloud iam roles describe DatabricksAdmin --project=YOUR_PROJECT_ID`


### Grant the service account the "Databricks Admin" role
`gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:privileged-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/DatabricksAdmin"`


### Download the keys.json file for caller-sa
`gcloud iam service-accounts keys create /path/to/caller-sa-key.json \
    --iam-account=caller-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com`

Replace `/path/to/caller-sa-key.json` with the desired local path and filename for the downloaded key file, and replace `YOUR_PROJECT_ID` with your actual GCP project ID. This command generates and downloads a JSON key file for the specified service account. The key file contains the private key and other information needed to authenticate as the service account.

### Authenticate using a service account (caller-sa) key file
`gcloud auth activate-service-account \
    --key-file=/path/to/caller-sa-key.json`

This command activates authentication with Google Cloud using the provided service account key file. Replace `/path/to/caller-sa-key.json` with the actual path to your `caller-sa` service account key file.


### Configure [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc) for caller-sa (Service Account) impersonating privileged-sa

### Set the environment variable for the path to the caller-sa key file
`export GOOGLE_APPLICATION_CREDENTIALS="/path/to/caller-sa-key.json"`

### Set gcloud configuration to impersonate the privileged-sa service account
`gcloud config set auth/impersonate_service_account privileged-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com`

### Set the GOOGLE_OAUTH_ACCESS_TOKEN environment variable to use the access token for creating GCP resources with gcloud
`export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)`

### Databricks Account Configuration

Follow these steps to add privileged-sa to the Databricks account console:

- [Login](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html#manage-users-in-your-account) into the account console.
- [Add](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html#add-users-to-your-account-using-the-account-console)  `privileged-sa` as an accounts user.
- [Assign](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html#assign-account-admin-roles-to-a-user) accounts admin role to `privileged-sa`.
- Please note that you should add only **privileged-sa** as a **user** in the Databricks account console.

**You are now ready to run Terraform scripts.**