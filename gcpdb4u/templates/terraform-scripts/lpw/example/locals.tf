# MODIFICATION: Phase configuration mapping
# Reason: Automatically derive expected_workspace_status and provision_workspace_resources from single phase variable
locals {
  # Normalize phase to uppercase for case-insensitive matching
  normalized_phase = upper(var.phase)

  phase_config = {
    PROVISIONING = {
      expected_workspace_status     = "PROVISIONING"
      provision_workspace_resources = false
    }
    RUNNING = {
      expected_workspace_status     = "RUNNING"
      provision_workspace_resources = true
    }
  }

  current_phase = local.phase_config[local.normalized_phase]

  # MODIFICATION: Safety check to prevent resource creation before workspace is RUNNING
  # Reason: Ensure workspace reaches RUNNING state before provisioning Unity Catalog resources
  # IMPORTANT: For destroy operations, always set to true to ensure ALL resources are destroyed
  # regardless of phase - prevents orphaned resources
  safe_provision_resources = local.current_phase.expected_workspace_status == "RUNNING" && local.current_phase.provision_workspace_resources
}

