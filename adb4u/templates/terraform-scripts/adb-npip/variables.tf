variable "prefix" {
  type    = string
  default = "bk"
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
  default = "user@company.com"
}

variable "tag_keepuntil" {
  type    = string
  default = "12/31/2024"
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
