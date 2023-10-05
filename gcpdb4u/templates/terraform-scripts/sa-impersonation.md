## Goal

Create Databricks workspace using Terraform & Service Account based authentication and impersonation.

### Create two service accounts

- **automation-sa:** Used to create Databricks workspace.
- **terraform-sa:** Used to impersonate automation-sa and run Terraform.

### Assign roles/permissions to service accounts

- **automation-sa:** Required [permissions](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/permissions.html#required-permissions-for-the-workspace-creator) to create a workspace on the service project. Project viewer role on the host or shared VPC project (if using shared VPC).
- **terraform-sa:** [Service Account Token Creator](https://cloud.google.com/iam/docs/understanding-roles#iam.serviceAccountTokenCreator) role on the automation-sa.

### Configure gcloud authentication

Run the following commands on the computer from where you are running Terraform. Before running them, create credentials aka [key file](https://cloud.google.com/iam/docs/keys-create-delete#creating) for the terraform-sa.

```
gcloud auth activate-service-account --key-file terraform-sa-creds.json
```

## Verification and Setup

### Verify that the gcloud auth is set

To ensure that your Google Cloud authentication is properly configured, run the following command:

```
gcloud auth list
```

### Set service account impersonation

To enable service account impersonation, use the following command:

```
gcloud config set auth/impersonate_service_account automation-sa@project.iam.gserviceaccount.com
```

## Databricks Account Configuration

Follow these steps to set up automation-sa in the Databricks account console:

- [Login](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html#manage-users-in-your-account) into the account console.
- [Add](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html#add-users-to-your-account-using-the-account-console) automation-sa as an accounts user.
- [Assign](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html#assign-account-admin-roles-to-a-user) accounts admin role to automation-sa.
- Please note that you should add only **automation-sa** as a **user** in the Databricks account console.

**You are now ready to run Terraform scripts.**