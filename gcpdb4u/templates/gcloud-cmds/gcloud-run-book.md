***REMOVED******REMOVED******REMOVED*** PSC workspace creation run book
***REMOVED******REMOVED******REMOVED*** You would need to update commands as per your environment details


Create a service account, lets call it automatio-sa and grant it:
grant projectViewer role on vpc project (if using shared vpc)
grant projectEditor and IAMAdmin role on service project i.e. where the workspace will be created or could add a custom role

***REMOVED******REMOVED******REMOVED*** Create Databricks custom role for ws creation
gcloud iam roles create DatabricksCustomRole \
    --project=aservice-prj2 \
    --title="Databricks Custom Role" \
    --description="Purpose built role for workspace provisioning" \
    --permissions=iam.serviceAccounts.getIamPolicy,iam.serviceAccounts.setIamPolicy,iam.roles.create,iam.roles.delete,iam.roles.get,iam.roles.update,resourcemanager.projects.get,resourcemanager.projects.getIamPolicy,resourcemanager.projects.setIamPolicy,serviceusage.services.get,serviceusage.services.list,serviceusage.services.enable,compute.networks.get,compute.projects.get,compute.subnetworks.get

***REMOVED******REMOVED******REMOVED*** Grant custom role to your service account
gcloud projects add-iam-policy-binding aservice-prj2 \
    --member="serviceAccount:automation-sa@aservice-prj2.iam.gserviceaccount.com" \
    --role="roles/DatabricksCustomRole"

***REMOVED******REMOVED******REMOVED*** Grant viewer role to the automation SA on the shared vpc project
gcloud projects add-iam-policy-binding ahost-prj \
    --member="serviceAccount:automation-sa@aservice-prj2.iam.gserviceaccount.com" \
    --role="roles/viewer"

***REMOVED******REMOVED******REMOVED*** List roles assigned to automation SA on service project
gcloud projects get-iam-policy aservice-prj2 \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:automation-sa@aservice-prj2.iam.gserviceaccount.com" \
    --format="table(bindings.role)"

***REMOVED******REMOVED******REMOVED*** List roles assigned to automation SA on host project
gcloud projects get-iam-policy ahost-prj \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:automation-sa@aservice-prj2.iam.gserviceaccount.com" \
    --format="table(bindings.role)"

***REMOVED******REMOVED******REMOVED*** On your local system where you plan to run terraform

***REMOVED******REMOVED******REMOVED*** Authenticate your gcloud session

gcloud auth application-default login

***REMOVED******REMOVED******REMOVED*** Set default project to Databricks project
***REMOVED******REMOVED******REMOVED*** PROJECT_NAME == Service or Host project

gcloud config set project PROJECT_NAME

***REMOVED******REMOVED******REMOVED*** Following command runs on vpc (host) project

gcloud config set project VPC_PROJECT_NAME

***REMOVED******REMOVED******REMOVED*** Create private ip addresses used for Databricks 
gcloud compute addresses create api-pe-ip --region=us-central1 --subnet=psc-endpoint-subnet
gcloud compute addresses list --filter="name=api-pe-ip"

gcloud compute addresses create relay-pe-ip --region=us-central1 --subnet=psc-endpoint-subnet
gcloud compute addresses list --filter="name=relay-pe-ip"

***REMOVED******REMOVED******REMOVED*** Create private endpoint using regional service serviceAttachments
***REMOVED******REMOVED******REMOVED*** Detailed list of per region attachement available over here
***REMOVED******REMOVED******REMOVED*** https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/private-service-connect.html***REMOVED***regional-endpoints

gcloud compute forwarding-rules create usc1-backend-ep \
    --region=us-central1 \
    --network=psc-vpc-svc-prj2-xpn \
    --address=relay-pe-ip \
    --target-service-attachment=projects/prod-gcp-us-central1/regions/us-central1/serviceAttachments/ngrok-psc-endpoint

gcloud compute forwarding-rules create usc1-frontend-ep \
    --region=us-central1 \
    --network=psc-vpc-svc-prj2-xpn \
    --address=api-pe-ip \
    --target-service-attachment=projects/prod-gcp-us-central1/regions/us-central1/serviceAttachments/plproxy-psc-endpoint

***REMOVED******REMOVED******REMOVED*** List private endpoints
gcloud compute forwarding-rules describe usc1-backend-ep \
    --region=us-central1

gcloud compute forwarding-rules describe usc1-frontend-ep \
    --region=us-central1


***REMOVED******REMOVED******REMOVED*** runs on gke (service) project
***REMOVED******REMOVED******REMOVED*** Create CMK keys for databricks
***REMOVED******REMOVED******REMOVED*** Key could reside in any project, service, host or any other project


gcloud config set project GKE_PROJECT_NAME

gcloud kms keyrings create databricks-keyring \
    --location us-central1

gcloud kms keyrings list --location=us-central1

gcloud kms keys create databricks-cmek \
    --keyring databricks-keyring \
    --location us-central1 \
    --purpose "encryption" \
    --protection-level "software"

gcloud kms keys list --location=us-central1 --keyring=databricks-keyring

***REMOVED******REMOVED******REMOVED*** Grant permission on the key to automation-SA

gcloud kms keys add-iam-policy-binding databricks-cmek \
  --location us-central1 \
  --keyring databricks-keyring \
  --member serviceAccount:automation-sa@aservice-prj2.iam.gserviceaccount.com \
  --role roles/cloudkms.admin

gcloud kms keys add-iam-policy-binding databricks-cmek \
  --location us-central1 \
  --keyring databricks-keyring \
  --member serviceAccount:automation-sa@aservice-prj2.iam.gserviceaccount.com \
  --role roles/cloudkms.viewer


***REMOVED******REMOVED******REMOVED*** create perimeter

***REMOVED*** replace the following with your details
***REMOVED*** projects/216220932942 - project you would like to secure
***REMOVED*** --policy=1075567926800 - policy id
***REMOVED*** --access-levels='accessPolicies/1075567926800/accessLevels/prod_access_policy' -  access context policy

gcloud access-context-manager perimeters create 'accessPolicies/1075567926800/servicePerimeters/dbxpolicy' \
  --title=labs-dbxpolicy \
  --resources=projects/216220932942 \
  --restricted-services=cloudresourcemanager.googleapis.com,compute.googleapis.com,container.googleapis.com,containerregistry.googleapis.com,iam.googleapis.com,storage.googleapis.com \
  --ingress-policies=ingress.yaml \
  --egress-policies=egress.yaml \
  --access-levels='accessPolicies/1075567926800/accessLevels/prod_access_policy' \
  --vpc-allowed-services=RESTRICTED-SERVICES \
  --policy=1075567926800

***REMOVED*** dry run
gcloud access-context-manager perimeters dry-run create 'accessPolicies/1075567926800/servicePerimeters/labsperimeter2' \
  --perimeter-title=labs-perimeter2 \
  --perimeter-type=regular \
  --perimeter-resources=projects/216220932942 \
  --perimeter-restricted-services=cloudresourcemanager.googleapis.com,compute.googleapis.com,container.googleapis.com,containerregistry.googleapis.com,iam.googleapis.com,storage.googleapis.com \
  --perimeter-ingress-policies=ingress.yaml \
  --perimeter-egress-policies=egress.yaml \
  --perimeter-access-levels='accessPolicies/1075567926800/accessLevels/prod_access_policy' \
  --perimeter-vpc-allowed-services=RESTRICTED-SERVICES \
  --policy=1075567926800

***REMOVED*** delete perimeter
gcloud access-context-manager perimeters dry-run delete labs_perimeter --policy 1075567926800