variable custom_tag_cost_center {}
variable custom_tag_team {}
variable cluster_policy1_name {}
locals {
  default_policy = {
    "dbus_per_hour" : {
      "type" : "range",
      "maxValue" : 10
    },
    "autotermination_minutes" : {
      "type" : "fixed",
      "value" : 20,
      "hidden" : true
    },
    "custom_tags.Team" : {
      "type" : "fixed",
      "value" : var.custom_tag_team
    },
    "custom_tags.CostCenter" : {
      "type" : "fixed",
      "value" : var.custom_tag_cost_center
    }
  }
}

resource "databricks_cluster_policy" "fair_use" {
  provider = databricks.workspace
  name       = "${var.cluster_policy1_name} cluster policy"
  definition = jsonencode(local.default_policy)

  depends_on = [
    databricks_mws_permission_assignment.add_non_admin_group,
    databricks_mws_permission_assignment.add_admin_group,
    databricks_grants.all_grants
  ]
}

resource "databricks_permissions" "can_use_cluster_policyinstance_profile" {
  provider = databricks.workspace
  cluster_policy_id = databricks_cluster_policy.fair_use.id
  access_control {
    group_name       = var.group_name1
    permission_level = "CAN_USE"
  }
  depends_on = [
    databricks_mws_permission_assignment.add_non_admin_group,
    databricks_mws_permission_assignment.add_admin_group,
    databricks_grants.all_grants
  ]
}