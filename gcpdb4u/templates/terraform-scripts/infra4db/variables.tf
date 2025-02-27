variable "vpc_project_id" {
  description = "The GCP project ID"
  type        = string
}

***REMOVED*** variable "vpc_project_region" {
***REMOVED***   description = "Default region for resources"
***REMOVED***   type        = string
***REMOVED*** }

variable "network_name" {
  description = "Name of the VPC network"
  type        = string
}

variable "subnet_configs" {
  description = "Subnet configurations including PSC subnets"
  type = map(object({
    region = string
    cidr   = string
    psc    = optional(bool, false)
  }))
}

variable "psc_subnet_configs" {
  description = "Subnet configurations for PSC subnets"
  type = map(object({
    region = string
    cidr   = string
  }))
}

variable "create_psc_resources" {
  description = "Flag to create PSC subnets, routes, and firewall rules"
  type        = bool
}

variable "destination_ips" {
  description = "Destination IPs for each region"
  type = map(string)
}

variable "databricks_hive_ips" {
  description = "Destination IPs for databricks managed hive for each region"
  type = map(string)
}

variable "create_cmk_resources" {
  description = "Flag to enable or disable the creation of KMS resources"
  type        = bool
  default     = false  ***REMOVED*** Set to true to enable KMS resource creation
}

variable "create_psc_endpoints" {
  description = "Flag to enable or disable the creation of PSC endpoints"
  type        = bool
  default     = false  ***REMOVED*** Set to true to enable PSC endpoint creation
}

variable "psc_attachments" {
  description = "Regional workspace and relay attachments"
  type = map(object({
    workspace_attachment = string
    relay_attachment     = string
  }))
}

variable "private_googleapi_ips" {
  type    = list(string)
  default = [
    "199.36.153.10",
    "199.36.153.11",
    "199.36.153.8",
    "199.36.153.9",
    "199.36.153.4",
    "199.36.153.5",
    "199.36.153.6",
    "199.36.153.7"
  ]
}