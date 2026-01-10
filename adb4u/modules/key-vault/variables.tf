***REMOVED*** ==============================================
***REMOVED*** Key Vault Configuration
***REMOVED*** ==============================================

variable "create_key_vault" {
  description = "Create new Key Vault (true) or use existing (false)"
  type        = bool
  default     = true
}

variable "existing_key_vault_id" {
  description = "ID of existing Key Vault (required if create_key_vault=false)"
  type        = string
  default     = ""
}

variable "existing_key_id" {
  description = "ID of existing CMK key in Key Vault (optional, will create if not provided)"
  type        = string
  default     = ""
}

variable "key_vault_name" {
  description = "Name of Key Vault (auto-generated if empty)"
  type        = string
  default     = ""
}

variable "key_name" {
  description = "Name of CMK key (default: databricks-cmk)"
  type        = string
  default     = "databricks-cmk"
}

***REMOVED*** ==============================================
***REMOVED*** Key Configuration
***REMOVED*** ==============================================

variable "key_type" {
  description = "Type of key (RSA, RSA-HSM, EC, EC-HSM)"
  type        = string
  default     = "RSA"
  
  validation {
    condition     = contains(["RSA", "RSA-HSM", "EC", "EC-HSM"], var.key_type)
    error_message = "key_type must be one of: RSA, RSA-HSM, EC, EC-HSM"
  }
}

variable "key_size" {
  description = "Size of RSA key (2048, 3072, 4096)"
  type        = number
  default     = 2048
  
  validation {
    condition     = contains([2048, 3072, 4096], var.key_size)
    error_message = "key_size must be one of: 2048, 3072, 4096"
  }
}

variable "key_opts" {
  description = "Key operations (decrypt, encrypt, sign, unwrapKey, verify, wrapKey)"
  type        = list(string)
  default     = ["decrypt", "encrypt", "unwrapKey", "wrapKey"]
}

variable "enable_auto_rotation" {
  description = "Enable automatic key rotation"
  type        = bool
  default     = true
}

variable "rotation_policy_days" {
  description = "Days after creation before key auto-rotates (minimum 28 days)"
  type        = number
  default     = 90
  
  validation {
    condition     = var.rotation_policy_days >= 28
    error_message = "rotation_policy_days must be at least 28 days"
  }
}

variable "expiry_days" {
  description = "Days until key expires (null for no expiration)"
  type        = number
  default     = null
}

***REMOVED*** ==============================================
***REMOVED*** Access Policy Configuration
***REMOVED*** ==============================================

variable "enable_purge_protection" {
  description = "Enable purge protection (recommended for production)"
  type        = bool
  default     = true
}

variable "enable_soft_delete" {
  description = "Enable soft delete (required for purge protection)"
  type        = bool
  default     = true
}

variable "soft_delete_retention_days" {
  description = "Days to retain soft-deleted keys (7-90)"
  type        = number
  default     = 90
  
  validation {
    condition     = var.soft_delete_retention_days >= 7 && var.soft_delete_retention_days <= 90
    error_message = "soft_delete_retention_days must be between 7 and 90"
  }
}

variable "databricks_principal_id" {
  description = "Azure Databricks Resource Provider principal ID (required for CMK)"
  type        = string
  default     = ""
}

***REMOVED*** ==============================================
***REMOVED*** Core Configuration
***REMOVED*** ==============================================

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "workspace_prefix" {
  description = "Prefix for naming resources"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
