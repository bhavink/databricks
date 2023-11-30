***REMOVED******REMOVED*** Goal

Create Databricks workspace using Terraform & Service Account based authentication and impersonation.
This documentation outlines the steps to create and configure two Google Cloud Platform (GCP) service accounts, namely caller-sa and privileged-sa. The caller-sa service account is granted the "Service Account Token Creator" role, while the privileged-sa service account is given the "Project Owner" role. The JSON key file for the caller-sa service account is also downloaded. Subsequently, the document provides instructions on authenticating with the service account key file using gcloud, initiating interactive login for user principal authentication, and configuring Application Default Credentials (ADC) for caller-sa to impersonate privileged-sa. The steps ensure proper setup and access control for subsequent interactions with GCP resources.
Please note that databricks terraform provider only support GCP Service Account based authentication. What this means is that
you have to create a service account with required permissions as explained below.

***REMOVED******REMOVED*** High level Steps

- Create the service account named caller-sa.
- Grant the "Service Account Token Creator" role to caller-sa.
- Create the service account named privileged-sa.
- Grant the "Project Owner" role to privileged-sa.
- Download the keys.json file for caller-sa:
- Activate authentication using the caller-sa service account key file.
- Alternatively Authenticate interactively using user principal (login):
- Configure Application Default Credentials (ADC) for caller-sa:
- Set the environment variable for the path to the caller-sa key file.
- Set gcloud configuration to impersonate the privileged-sa service account.
- Set the GOOGLE_OAUTH_ACCESS_TOKEN environment variable for creating GCP resources.

***REMOVED******REMOVED******REMOVED*** Create two service accounts

- **caller-sa:** Low privileged sa, used to impersonate privileged sa.
- **privileged-sa:** Used to create databricks and gcp resources.

***REMOVED******REMOVED******REMOVED*** Assign roles/permissions to service accounts

- **privileged-sa:** Required [permissions](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/permissions.html***REMOVED***required-permissions-for-the-workspace-creator) to create a workspace on the service project. Project viewer role on the host or shared VPC project (if using shared VPC).
- **caller-sa:** [Service Account Token Creator](https://cloud.google.com/iam/docs/understanding-roles***REMOVED***iam.serviceAccountTokenCreator) role on the automation-sa.

Make sure to replace following items with actual values

- YOUR_PROJECT_ID: Replace with your actual GCP project ID.
- /path/to/caller-sa-key.json: Replace with the desired local path and filename for the downloaded key file.


**Create caller-sa Service Account**

***REMOVED*** Create the service account
gcloud iam service-accounts create caller-sa --display-name="Caller Service Account"

***REMOVED*** Grant the service account the "Service Account Token Creator" role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:caller-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountTokenCreator"

**Create privileged-sa Service Account**

***REMOVED*** Create the service account
gcloud iam service-accounts create privileged-sa --display-name="Privileged Service Account"

***REMOVED*** Grant the service account the "Project Owner" role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:privileged-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/owner"

***REMOVED*** Download the keys.json file for caller-sa
gcloud iam service-accounts keys create /path/to/caller-sa-key.json \
    --iam-account=caller-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com

Replace /path/to/caller-sa-key.json with the desired local path and filename for the downloaded key file, and replace YOUR_PROJECT_ID with your actual GCP project ID. This command generates and downloads a JSON key file for the specified service account. The key file contains the private key and other information needed to authenticate as the service account.

***REMOVED*** Authenticate using a service account (caller-sa) key file
gcloud auth activate-service-account \
    --key-file=/path/to/caller-sa-key.json

This command activates authentication with Google Cloud using the provided service account key file. Replace /path/to/caller-sa-key.json with the actual path to your caller-sa service account key file.


***REMOVED*** Authenticate interactively using user principal (login)
gcloud auth login

This command initiates an interactive login process, allowing the user to authenticate and authorize gcloud to access Google Cloud resources on their behalf. It's useful when you want to use your personal user account for authentication.

***REMOVED*** Configure Application Default Credentials (ADC) for caller-sa (Service Account) impersonating privileged-sa
***REMOVED*** Reference: https://cloud.google.com/docs/authentication/provide-credentials-adc

***REMOVED*** Set the environment variable for the path to the caller-sa key file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/caller-sa-key.json"

***REMOVED*** Set gcloud configuration to impersonate the privileged-sa service account
gcloud config set auth/impersonate_service_account privileged-sa@bk-demo-service-prj2.iam.gserviceaccount.com

***REMOVED*** Set the GOOGLE_OAUTH_ACCESS_TOKEN environment variable to use the access token for creating GCP resources with gcloud
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)

***REMOVED******REMOVED*** Databricks Account Configuration

Follow these steps to set up privileged-sa in the Databricks account console:

- [Login](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html***REMOVED***manage-users-in-your-account) into the account console.
- [Add](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html***REMOVED***add-users-to-your-account-using-the-account-console) automation-sa as an accounts user.
- [Assign](https://docs.gcp.databricks.com/administration-guide/users-groups/users.html***REMOVED***assign-account-admin-roles-to-a-user) accounts admin role to automation-sa.
- Please note that you should add only **privileged-sa** as a **user** in the Databricks account console.

**You are now ready to run Terraform scripts.**