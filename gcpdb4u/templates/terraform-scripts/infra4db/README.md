# Terraform Configuration for Databricks VPC and PSC Setup

## Overview

This Terraform configuration is designed to set up a Virtual Private Cloud (VPC) in Google Cloud Platform (GCP) for Databricks, including the creation of subnets, Private Service Connect (PSC) subnets, and necessary firewall rules. It also includes the option to create Customer Managed Keys (CMK) for encryption.

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
- `create_psc_resources`: Flag to enable or disable the creation of PSC resources.
- `create_cmk_resources`: Flag to enable or disable the creation of KMS resources.

### `terraform.tfvars`

This file contains the values for the variables defined in `variables.tf`. You can customize the values according to your requirements. Key configurations include:

- `vpc_project_id`: Your GCP project ID.
- `network_name`: The desired name for the VPC.
- `subnet_configs`: Define the subnets you want to create.
- `psc_subnet_configs`: Define the PSC subnets you want to create.
- `psc_attachments`: Define the workspace and relay attachments for each region.

## Usage

1. **Clone the Repository**: Clone this repository to your local machine.

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Set Up Your Environment**: Ensure that your Google Cloud SDK is authenticated and configured to use the correct project.

   ```bash
   gcloud auth login
   gcloud config set project <your-project-id>
   ```

3. **Initialize Terraform**: Run the following command to initialize Terraform and download the necessary provider plugins.

   ```bash
   terraform init
   ```

4. **Plan the Deployment**: Generate an execution plan to see what resources will be created.

   ```bash
   terraform plan
   ```

5. **Apply the Configuration**: Apply the Terraform configuration to create the resources in GCP.

   ```bash
   terraform apply
   ```

   Confirm the action when prompted.

6. **Verify Resources**: After the apply completes, you can verify the created resources in the GCP Console.

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For any issues or questions, please contact the project maintainer or open an issue in the repository.
