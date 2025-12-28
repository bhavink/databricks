resource "random_string" "suffix" {
  length  = 10
  special = false
  upper   = false
  lower   = true
  numeric = true
}
