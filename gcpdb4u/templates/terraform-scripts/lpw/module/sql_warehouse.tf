resource "databricks_sql_endpoint" "this" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? local.sqlwarehouse_config_map : {}

  name                      = each.value.name
  cluster_size              = local.sql_config[each.value.config.type].cluster_size
  max_num_clusters          = tonumber(each.value.config.max_instance)
  enable_serverless_compute = (each.value.config.serverless == "true") ? true : false
  timeouts {
    create = "30m"
  }

  tags {
    custom_tags {
      key   = "ssp"
      value = var.ssp
    }
    custom_tags {
      key   = "apm"
      value = var.apmid
    }
    custom_tags {
      key   = "costcenter"
      value = var.costcenter
    }
    custom_tags {
      key   = "trproductid"
      value = var.trproductid
    }
    custom_tags {
      key   = "environment"
      value = var.environment
    }
    custom_tags {
      key   = "gcp_project"
      value = var.gcpprojectid
    }
    custom_tags {
      key   = "region"
      value = var.google_region
    }
  }

  depends_on = [null_resource.wait_for_workspace_running]
}