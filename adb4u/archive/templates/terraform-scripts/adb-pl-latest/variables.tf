variable "prefix" {
  type    = string
  default = "BK"
}

variable "tag_environment" {
  type    = string
  default = "Production"
}

variable "tag_pricing" {
  type    = string
  default = "Premium"
}

variable "tag_owner" {
  type    = string
  default = "bhavin.kukadia@databricks.com"
}

variable "tag_keepuntil" {
  type    = string
  default = "12/31/2026"
}

variable "adb_vnet_cidr" {
  type    = list(string)
  default = ["10.39.0.0/24"]
}

variable "adb_host_subnet" {
  type    = list(string)
  default = ["10.39.0.0/26"]
}

variable "adb_container_subnet" {
  type    = list(string)
  default = ["10.39.0.64/26"]
}

variable "adb_ws_user1" {
  type    = string
  default = "bhavin.kukadia@databricks.com"
}
