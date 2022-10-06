## Customize Default Compute SA Role

GCP projects that have enabled the Compute Engine API have a `Compute Engine default service account`, which has the following email:


`PROJECT_NUMBER-compute@developer.gserviceaccount.com`

Google creates the Compute Engine default service account and adds it to your project automatically but you have full control over the account.

The Compute Engine default service account is created with the IAM project editor role, but you can modify the service account's roles to securely limit which Google APIs the service account can access.

It is better to downscope the role assigned to this default account using gcp cloud shell as show below, please replace {{project-id}} with your project id which happens to be a numerical value

By default when a GKE cluster is created with no service account attached to it, GCP would use the default compute engine SA. Databricks requires the following permissons on the SA used by GKE

- compute.disks.get
- compute.disks.setLabels
- compute.instances.get
- compute.instances.setLabels

GCP IAM requires roles to be assigned to SA so in order to downscope the default compute SA role first we need to

- create a custom role with these permissions
- remove editor role from the default compute engine SA
- assign custom role to the default compute engine SA

Please replace {{project-id}} and {{project-number}} with relevant values.

### Get current role’s assigned to default compute SA

```
gcloud projects get-iam-policy {{project-id}}  \
--flatten="bindings[].members" \
--format='table(bindings.role)' \
--filter="bindings.members:{{project-number}}-compute@developer.gserviceaccount.com"
```

### Remove project editor role from default compute SA
```
gcloud projects remove-iam-policy-binding {{project-id}} \
--member "serviceAccount:{{project-number}}-compute@developer.gserviceaccount.com" \
--role roles/editor
```

### Create custom role
```
gcloud iam roles create databricksComputeSA \
--project {{project-id}} \
--title "Down scoped role for default compute SA" \
--description "This role has only the bare minimum permission's required by databricks to set labels on gke resources" \
--permissions compute.disks.get,compute.disks.setLabels,compute.instances.get,compute.instances.setLabels
```
### Assign custom role to default compute SA
```
gcloud projects add-iam-policy-binding {{project-id}} \
--member='serviceAccount:{{project-number}}-compute@developer.gserviceaccount.com' \
--role='projects/{{project-id}}/roles/databricksComputeSA'
```
### Validate current role’s assigned to default compute SA

```
gcloud projects get-iam-policy {{project-id}}  \
--flatten="bindings[].members" \
--format='table(bindings.role)' \
--filter="bindings.members:{{project-number}}-compute@developer.gserviceaccount.com"
```

### Optionally, add stackdriver related role’s to the default compute SA for logging and monitoring

```
gcloud projects add-iam-policy-binding {{project-id}} \
--member "serviceAccount:{{project-id}}-compute@developer.gserviceaccount.com" \
--role roles/monitoring.metricWriter
```

```
gcloud projects add-iam-policy-binding {{project-id}} \
--member "serviceAccount:{{project-id}}-compute@developer.gserviceaccount.com" \
--role roles/monitoring.viewer
```

```
gcloud projects add-iam-policy-binding {{project-id}} \
--member "serviceAccount:{{project-id}}-compute@developer.gserviceaccount.com" \
--role roles/stackdriver.resourceMetadata.writer
```

### Validate roles assigned to default compute SA


```
gcloud projects get-iam-policy {{project-id}}  \
--flatten="bindings[].members" \
--format='table(bindings.role)' \
--filter="bindings.members:{{project-id}}-compute@developer.gserviceaccount.com"
```



