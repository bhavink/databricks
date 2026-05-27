# Terraform Configuration for Databricks VPC and PSC Setup

## Overview

This Terraform configuration is designed to set up Google Cloud Platform (GCP) infrastructure required to create a Databricks workspace within customers GCP project including the creation of subnets, Private Service Connect (PSC) subnets, and necessary firewall rules. It also includes the option to create Customer Managed Keys (CMK) for encryption. Please note that we are only creating pre-requistes required to provision a Databricks workspace. Depending upon your needs you could create workspaces:

- [Bring Your Own(BYO) VPC](https://docs.databricks.com/gcp/en/security/network/classic/customer-managed-vpc)
  - When `create_psc_resources` and `create_cmk_resources` set to `false` in `terraform.tfvars`
- [BYOVPC + Private Service Connect(PSC)](https://docs.databricks.com/gcp/en/security/network/classic/private-service-connect)
  - When `create_psc_resources` set to `true` in `terraform.tfvars`
- [BYOVPC + CMK](https://docs.databricks.com/gcp/en/security/keys/customer-managed-keys)
  - When `create_cmk_resources` set to `true` in `terraform.tfvars`
- BYOVPC + PSC + Customer Managed Keys(CMK)
  - When `create_psc_resources` and `create_cmk_resources` set to `true` in `terraform.tfvars`
## Prerequisites

- **Terraform**: Ensure you have Terraform installed on your local machine. You can download it from [Terraform's official website](https://www.terraform.io/downloads.html).
- **Google Cloud SDK**: Install the Google Cloud SDK to interact with GCP. You can find installation instructions [here](https://cloud.google.com/sdk/docs/install).
- **GCP Project**: You need a GCP project where you have permissions to create resources.

## Required IAM Roles

To successfully create the resources defined in this Terraform configuration, ensure that the service account or user account you are using has the following IAM roles:

- **Project Owner**: Grants full control over all resources in the project.
- **DNS Admin**: Required to create and manage Private DNS zones and add DNS records.
- **KMS Admin**: Required to create and manage Customer Managed Keys (CMK).
- **Compute Admin**: Required to create and manage Compute Engine resources, including VPC networks and subnets.
- **Service Networking Admin**: Required to manage Private Service Connect and associated resources.
- **Viewer**: Grants read access to all resources in the project.

## Configuration Files

### `variables.tf`

This file defines the variables used in the Terraform configuration. Key variables include:

- `vpc_project_id`: The GCP project ID where the VPC will be created.
- `network_name`: The name of the VPC network.
- `subnet_configs`: Configurations for the subnets, including region and CIDR.
- `psc_subnet_configs`: Configurations for the PSC subnets.
- `create_psc_resources`: Flag to enable or disable the creation of PSC resources.This allows us to create a BYOVPC + PSC workspace
- `create_cmk_resources`: Flag to enable or disable the creation of KMS resources. This allows us to create a BYOVPC + CMK workspace

### `terraform.tfvars`

This file contains the values for the variables defined in `variables.tf`. You can customize the values according to your requirements. Key configurations include:

- `vpc_project_id`: Your GCP project ID.
- `network_name`: The desired name for the VPC.
- `subnet_configs`: Define the subnets you want to create.
- `psc_subnet_configs`: Define the PSC subnets you want to create.
- `psc_attachments`: Define the workspace and relay attachments for each region.
- `create_psc_resources`: Flag to enable or disable the creation of PSC resources.
- `create_cmk_resources`: Flag to enable or disable the creation of KMS resources.

## Usage

1. **Rename terraform.tfvars.remove**: Rename terraform.tfvars.remove by removing `remove` from the end of the file extension. Update variables so that it has your desired values

2. **Initialize Terraform**: Run the following command to initialize Terraform and download the necessary provider plugins.

   ```bash
   terraform init
   ```

3. **Plan the Deployment**: Generate an execution plan to see what resources will be created.

   ```bash
   terraform plan
   ```

4. **Apply the Configuration**: Apply the Terraform configuration to create the resources in GCP.

   ```bash
   terraform apply
   ```

   Confirm the action when prompted.

5. **Verify Resources**: After the apply completes, you can verify the created resources in the GCP Console or by running

   ```bash
   terraform output
   ```

## Cleanup

To destroy all resources created by this configuration, run:

```bash
terraform destroy
```

Confirm the action when prompted.

## Notes

- Ensure that you have the necessary permissions in your GCP project to create the resources defined in this configuration.
- Modify the `terraform.tfvars` file to customize the setup according to your needs.
- The configuration includes commented-out sections for additional regions. Uncomment and modify as needed.

## Subnet Lifecycle & Sharing Patterns

This module creates the node subnets and (optionally) PSC subnets that downstream workspace configs consume. Two GA-supported patterns are worth calling out before you provision:

### 1. Swapping an existing workspace's subnet (GA)

The IP range of a deployed workspace cannot be resized in place, but the workspace can be **moved to a different subnet** in the same VPC after creation:

1. Add the new subnet here (extend `subnet_configs` with a new key, or create a sibling subnet in the same VPC).
2. Grant the workspace SA the **Databricks Network Role v2** on the new subnet.
3. Create a new Databricks network configuration object referencing the new subnet.
4. `PATCH /api/2.0/accounts/{account_id}/workspaces/{workspace_id}` to switch the workspace over (terminate running clusters/jobs first).

The customer-managed VPC itself remains immutable post-creation — only the subnet inside it can change. Reference: [Update workspace network configuration](https://docs.databricks.com/gcp/en/security/network/classic/update-workspaces).

### 2. Multiple workspaces in one subnet (GA, not recommended)

`subnet_configs` is keyed by region — a single entry produces a single subnet that any number of workspaces can attach to. Sharing one subnet across workspaces is **GA-supported** but the default recommendation is still one subnet per workspace.

Use shared subnets only when:
- IP address space is genuinely constrained, or
- You are deliberately consolidating a shared compute-plane VPC across many workspaces.

When sharing, size the subnet's CIDR for the **sum** of cluster IP demand across every workspace that will live in it. Per-workspace isolation, blast radius, and chargeback all degrade — see [Workspace-Architecture.md → Multiple workspaces sharing a single subnet](../../../Workspace-Architecture.md#multiple-workspaces-sharing-a-single-subnet-ga) for the full trade-off matrix.

