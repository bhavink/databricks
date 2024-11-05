variable "spokecidr" {
  type    = string
  default = "10.178.0.0/20"
}

variable "no_public_ip" {
  type    = bool
  default = true
}

variable "rglocation" {
  type    = string
  default = "westus"
}

variable "dbfs_prefix" {
  type    = string
  default = "dbfs"
}

variable "workspace_prefix" {
  type    = string
  default = "dbwbk"
}

variable "admin_user" {
  type    = string
  default = "bhavin.kukadia@databricks.com"
}

variable "uc_root_storage"{
  type = string
  default = "ucrootstorage"
}

variable "uc_ext_storage"{
  type = string
  default = "ucextstorage1"
}

variable "environment"{
  type = string
  default = "Testing"
}

variable "tags_environment" {
  type = string
  default = "Testing"
}
variable "tags_owner" {
  type = string
  default = "bhavin.kukadia@databricks.com"
}
variable "tags_keepuntil"{
  type = string
  default = "12/31/2025"
}
variable "tags_epoch"{
  type = string
  default = ""
}