## Customize Default Compute SA Role

GCP projects that have enabled the Compute Engine API have a `Compute Engine default service account`, which has the following email:


`PROJECT_NUMBER-compute@developer.gserviceaccount.com`

Google creates the Compute Engine default service account and adds it to your project automatically but you have full control over the account.

The Compute Engine default service account is created with the IAM project editor role, but you can modify the service account's roles to securely limit which Google APIs the service account can access.

You can disable or delete this service account from your project, but doing so might cause any applications that depend on the service account's credentials to fail most notably GKE.

As per CIS recommendation, it is better to downscope the role assigned to this default account using gcp cloud shell as show below, please replace {{project-id}} with your project id which happens to be a numerical value

Get current role’s assigned to default compute SA

```
gcloud projects get-iam-policy {{project-id}}  \
--flatten="bindings[].members" \
--format='table(bindings.role)' \
--filter="bindings.members:{{project-id}}-compute@developer.gserviceaccount.com"
Add required minimum role’s to default compute SA
```


```
gcloud projects add-iam-policy-binding {{project-id}} \
--member "serviceAccount:{{project-id}}-compute@developer.gserviceaccount.com" \
--role roles/logging.logWriter
```

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

Remove project editor role from default compute SA

```
gcloud projects remove-iam-policy-binding {{project-id}} \
--member "serviceAccount:{{project-id}}-compute@developer.gserviceaccount.com" \
--role roles/editor
```

Validate roles assigned to default compute SA


```
gcloud projects get-iam-policy {{project-id}}  \
--flatten="bindings[].members" \
--format='table(bindings.role)' \
--filter="bindings.members:{{project-id}}-compute@developer.gserviceaccount.com"
```



