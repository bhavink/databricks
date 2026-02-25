locals {

  # Databricks Account Configuration
  databricks_account_id  = var.databricks_account_id
  databricks_account_url = "https://accounts.gcp.databricks.com"

  small_node_type  = "${var.node_type}-standard-4"
  medium_node_type = "${var.node_type}-standard-8"
  large_node_type  = "${var.node_type}-standard-16"
  all_node_types   = "${var.node_type}-standard-4,${var.node_type}-standard-8,${var.node_type}-standard-16,${var.node_type}-standard-32,${var.node_type}-highmem-4,${var.node_type}-highmem-8,${var.node_type}-highmem-16,${var.node_type}-highmem-32"

  # Personal compute node types - uses all available node types by default
  personal_compute_nodes = split(",", local.all_node_types)
  personal_compute_node_types = {
    "node_type_id" : {
      "type" : "allowlist",
      "values" : local.personal_compute_nodes,
      "defaultValue" : local.personal_compute_nodes[0]
    }
  }

  # Regional Configuration - Private Access and VPC Endpoints
  # Provided via variables - these are region-specific identifiers
  private_access_settings_id      = var.private_access_settings_id
  dataplane_relay_vpc_endpoint_id = var.dataplane_relay_vpc_endpoint_id # ngrok
  rest_api_vpc_endpoint_id        = var.rest_api_vpc_endpoint_id        # plproxy
  databricks_metastore_id         = var.databricks_metastore_id         # Unity Catalog metastores

  pool_configs = {
    Small = {
      name         = "Small Pool"
      max_capacity = 32
      node_type    = "${var.node_type}-standard-4"
    }
    Medium = {
      name         = "Medium Pool"
      max_capacity = 64
      node_type    = "${var.node_type}-standard-8"
    }
    Large = {
      name         = "Large Pool"
      max_capacity = 128
      node_type    = "${var.node_type}-standard-16"
    }
  }
  default_compute_timeout = {
    "autotermination_minutes" : {
      "type" : "fixed",
      "value" : 30
    }
  }

  policies = {
    Small = {
      Job_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 2
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 8,
          "defaultValue" : 4
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 16
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.small_node_type
        },
        "cluster_type" : {
          "type" : "fixed",
          "value" : "job"
        }
      }
      Job_Pool_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 2
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 8,
          "defaultValue" : 4
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 16
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.small_node_type
        },
        "cluster_type" : {
          "type" : "fixed",
          "value" : "job"
        },
        "instance_pool_id" : {
          "type" : "unlimited",
          "isOptional" : true,
          "defaultValue" : can(databricks_instance_pool.compute_pools["Small"]) ? databricks_instance_pool.compute_pools["Small"].instance_pool_id : null
        }
      }
      All_Purpose_Pool_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 2
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 8,
          "defaultValue" : 4
        },
        "autotermination_minutes" : {
          "type" : "fixed",
          "value" : 60
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 16
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.small_node_type
        },
        "instance_pool_id" : {
          "type" : "unlimited",
          "isOptional" : true,
          "defaultValue" : can(databricks_instance_pool.compute_pools["Small"]) ? databricks_instance_pool.compute_pools["Small"].instance_pool_id : null
        }
      }
      All_Purpose_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 2
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 8,
          "defaultValue" : 4
        },
        "autotermination_minutes" : {
          "type" : "fixed",
          "value" : 60
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 16
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.small_node_type
        }
      }
    }
    Medium = {
      Job_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 4
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 16,
          "defaultValue" : 8
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 32
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.medium_node_type
        },
        "cluster_type" : {
          "type" : "fixed",
          "value" : "job"
        }
      }
      Job_Pool_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 4
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 16,
          "defaultValue" : 8
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 32
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.medium_node_type
        },
        "cluster_type" : {
          "type" : "fixed",
          "value" : "job"
        },
        "instance_pool_id" : {
          "type" : "unlimited",
          "isOptional" : true,
          "defaultValue" : can(databricks_instance_pool.compute_pools["Medium"]) ? databricks_instance_pool.compute_pools["Medium"].instance_pool_id : null
        }
      }
      All_Purpose_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 4
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 16,
          "defaultValue" : 8
        },
        "autotermination_minutes" : {
          "type" : "fixed",
          "value" : 60
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 32
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.medium_node_type
        }
      }
      All_Purpose_Pool_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 4
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 16,
          "defaultValue" : 8
        },
        "autotermination_minutes" : {
          "type" : "fixed",
          "value" : 60
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 32
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.medium_node_type
        },
        "instance_pool_id" : {
          "type" : "unlimited",
          "isOptional" : true,
          "defaultValue" : can(databricks_instance_pool.compute_pools["Medium"]) ? databricks_instance_pool.compute_pools["Medium"].instance_pool_id : null
        }
      }
    }
    Large = {
      Job_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 4
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 16,
          "defaultValue" : 8
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 64
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.large_node_type
        },
        "cluster_type" : {
          "type" : "fixed",
          "value" : "job"
        }
      }
      Job_Pool_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 4
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 16,
          "defaultValue" : 8
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 64
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.large_node_type
        },
        "cluster_type" : {
          "type" : "fixed",
          "value" : "job"
        },
        "instance_pool_id" : {
          "type" : "unlimited",
          "isOptional" : true,
          "defaultValue" : can(databricks_instance_pool.compute_pools["Large"]) ? databricks_instance_pool.compute_pools["Large"].instance_pool_id : null
        }
      }
      All_Purpose_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 4
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 16,
          "defaultValue" : 8
        },
        "autotermination_minutes" : {
          "type" : "fixed",
          "value" : 60
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 64
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.large_node_type
        }
      }
      All_Purpose_Pool_Policy = {
        "autoscale.min_workers" : {
          "type" : "range",
          "minValue" : 1,
          "defaultValue" : 4
        },
        "autoscale.max_workers" : {
          "type" : "range",
          "maxValue" : 16,
          "defaultValue" : 8
        },
        "autotermination_minutes" : {
          "type" : "fixed",
          "value" : 60
        },
        "dbus_per_hour" : {
          "type" : "range",
          "maxValue" : 64
        },
        "node_type_id" : {
          "type" : "allowlist",
          "values" : split(",", local.all_node_types),
          "defaultValue" : local.large_node_type
        },
        "instance_pool_id" : {
          "type" : "unlimited",
          "isOptional" : true,
          "defaultValue" : can(databricks_instance_pool.compute_pools["Large"]) ? databricks_instance_pool.compute_pools["Large"].instance_pool_id : null
        }
      }
    }
  }

  common_policy = {
    "spark_version" : {
      "type" : "regex",
      "pattern" : "(1.*\\..*)"
    },
    "spark_conf.spark.databricks.sql.initial.catalog.name" : {
      "type" : "fixed",
      "value" : "main",
      "hidden" : true
    },
    "spark_conf.spark.hadoop.datanucleus.fixedDatastore" : {
      "type" : "fixed",
      "value" : "false"
    },
    "spark_conf.spark.hadoop.javax.jdo.option.ConnectionDriverName" : {
      "type" : "fixed",
      "value" : "org.apache.derby.jdbc.EmbeddedDriver"
    },
    "spark_conf.spark.hadoop.javax.jdo.option.ConnectionURL" : {
      "type" : "fixed",
      "value" : "jdbc:derby:memory:myInMemDB;create=true"
    },
    "spark_conf.spark.hadoop.javax.jdo.option.ConnectionUserName" : {
      "type" : "fixed",
      "value" : "hiveuser"
    },
    "spark_conf.spark.hadoop.javax.jdo.option.ConnectionPassword" : {
      "type" : "fixed",
      "value" : "hivepass"
    },
    "spark_conf.spark.hadoop.datanucleus.autoCreateSchema" : {
      "type" : "fixed",
      "value" : "true"
    },
    "spark_conf.spark.hadoop.datanucleus.autoCreateTables" : {
      "type" : "fixed",
      "value" : "true"
    },
    "spark_conf.spark.sql.catalogImplementation" : {
      "type" : "fixed",
      "value" : "hive"
    }
  }


  common_tags = {
    "custom_tags.org" : {
      "type" : "fixed",
      "value" : var.org
    },
    "custom_tags.apmid" : {
      "type" : "fixed",
      "value" : var.apmid
    },
    "custom_tags.trproductid" : {
      "type" : "fixed",
      "value" : var.trproductid
    },
    "custom_tags.ssp" : {
      "type" : "fixed",
      "value" : var.ssp
    },
    "custom_tags.gcpprojectid" : {
      "type" : "fixed",
      "value" : var.gcpprojectid
    },
    "custom_tags.costcenter" : {
      "type" : "fixed",
      "value" : var.costcenter
    },
    "custom_tags.teamname" : {
      "type" : "fixed",
      "value" : var.teamname
    },
    "custom_tags.owner" : {
      "type" : "fixed",
      "value" : replace(replace(var.owner, "@", "_at_"), ".", "_dot_")
    },
    "custom_tags.environment" : {
      "type" : "fixed",
      "value" : var.environment
    },
    "custom_tags.notificationdistlist" : {
      "type" : "fixed",
      "value" : replace(replace(var.notificationdistlist, "@", "_at_"), ".", "_dot_")
    },
    "custom_tags.workspaceid" : {
      "type" : "fixed",
      "value" : tostring(databricks_mws_workspaces.dbx_workspace.workspace_id)
    },
    "custom_tags.workspacename" : {
      "type" : "fixed",
      "value" : databricks_mws_workspaces.dbx_workspace.workspace_name
    },
    "custom_tags.applicationname" : {
      "type" : "fixed",
      "value" : databricks_mws_workspaces.dbx_workspace.workspace_name
    }
  }
}



# Flattening the nested maps for all policies, but filter based on variable `policy_type`
locals {
  all_policies = flatten([
    for policy_type, policy_map in local.policies : [
      for policy_key, policy_value in policy_map : {
        type  = policy_type
        name  = policy_key
        value = policy_value
      } if contains(split(",", var.compute_types), policy_type) # Apply filter based on `policy_type`
    ]
  ])

  # MODIFICATION - added check to make sure that workspace is in running state before provisioning workspace resources
  # Create map for cluster policies - only when workspace resources should be provisioned
  cluster_policies_map = {
    for policy in local.all_policies :
    "${policy.type}_${policy.name}" => policy
    if var.provision_workspace_resources
  }
}



#ext_unity catalog converter
locals {

  json_compatible_ext_unity_catalog_config = (var.ext_unity_catalog_config != "") ? replace(var.ext_unity_catalog_config, "'", "\"") : ""
  ext_unity_catalog_config_list            = (local.json_compatible_ext_unity_catalog_config != "") ? (jsondecode(local.json_compatible_ext_unity_catalog_config)) : []
  ext_unity_catalog_config_map = {
    for idx, config in local.ext_unity_catalog_config_list : idx => config
  }
}

#ext_unity catalog permission 

locals {
  json_compatible_ext_unity_catalog_permissions = (var.ext_unity_catalog_permissions != "") ? replace(var.ext_unity_catalog_permissions, "'", "\"") : ""
  ext_unity_catalog_perm_list                   = (local.json_compatible_ext_unity_catalog_permissions != "") ? (jsondecode(local.json_compatible_ext_unity_catalog_permissions)) : []
  ext_unity_catalog_permissions_map = {
    for idx, config in local.ext_unity_catalog_perm_list : idx => config
  }
}


#unity catalog converter
locals {

  json_compatible_unity_catalog_config = (var.unity_catalog_config != "") ? replace(var.unity_catalog_config, "'", "\"") : ""
  unity_catalog_config_list            = (local.json_compatible_unity_catalog_config != "") ? (jsondecode(local.json_compatible_unity_catalog_config)) : []
  unity_catalog_config_map = {
    for idx, config in local.unity_catalog_config_list : idx => config
  }
}

#unity catalog permission 

locals {
  json_compatible_unity_catalog_permissions = (var.unity_catalog_permissions != "") ? replace(var.unity_catalog_permissions, "'", "\"") : ""
  unity_catalog_perm_list                   = (local.json_compatible_unity_catalog_permissions != "") ? (jsondecode(local.json_compatible_unity_catalog_permissions)) : []
  unity_catalog_permissions_map = {
    for idx, config in local.unity_catalog_perm_list : idx => config
  }
}


#external location permissions
locals {
  json_compatible_external_location_permissions = (var.external_location_permissions != "") ? replace(var.external_location_permissions, "'", "\"") : ""
  external_location_perm_list                   = (local.json_compatible_external_location_permissions != "") ? (jsondecode(local.json_compatible_external_location_permissions)) : []
  external_location_permissions_map = {
    for idx, config in local.external_location_perm_list : idx => config
  }
}


#storage location permissions
locals {
  json_compatible_storage_credentials_permissions = (var.storage_credentials_permissions != "") ? replace(var.storage_credentials_permissions, "'", "\"") : ""
  storage_credentials_perm_list                   = (local.json_compatible_storage_credentials_permissions != "") ? (jsondecode(local.json_compatible_storage_credentials_permissions)) : []
  storage_credentials_permissions_map = {
    for idx, config in local.storage_credentials_perm_list : idx => config
  }
}

#permissions group
locals {
  permissions_group_role_admin_list = (var.permissions_group_role_admin != "") ? split(",", var.permissions_group_role_admin) : []
  create_group_admin                = length(local.permissions_group_role_admin_list) > 0

  permissions_group_role_user_list = (var.permissions_group_role_user != "") ? split(",", var.permissions_group_role_user) : []
  create_group_user                = length(local.permissions_group_role_user_list) > 0
}

#permission users
locals {
  permissions_user_role_admin_list = (var.permissions_user_role_admin != "") ? split(",", var.permissions_user_role_admin) : []
  create_user_admin                = length(local.permissions_user_role_admin_list) > 0

  permissions_user_role_user_list = (var.permissions_user_role_user != "") ? split(",", var.permissions_user_role_user) : []
  create_user_user                = length(local.permissions_user_role_user_list) > 0
}

#permission spn
locals {
  permissions_spn_role_admin_list = (var.permissions_spn_role_admin != "") ? split(",", var.permissions_spn_role_admin) : []
  create_spn_admin                = length(local.permissions_spn_role_admin_list) > 0

  permissions_spn_role_user_list = (var.permissions_spn_role_user != "") ? split(",", var.permissions_spn_role_user) : []
  create_spn_user                = length(local.permissions_spn_role_user_list) > 0
}

#sql warehouse
locals {
  json_compatible_sqlwarehouse_config = (var.sqlwarehouse_cluster_config != "") ? replace(var.sqlwarehouse_cluster_config, "'", "\"") : ""
  sqlwarehouse_cluster_config_list    = (local.json_compatible_sqlwarehouse_config != "") ? (jsondecode(local.json_compatible_sqlwarehouse_config)) : []
  sqlwarehouse_config_map = {
    for idx, config in local.sqlwarehouse_cluster_config_list : idx => config
  }
}


locals {
  sql_config = {
    x-small = {
      name             = "sql_warehouse_x_small_${random_string.suffix.result}"
      cluster_size     = "X-Small"
      max_num_clusters = can(local.sqlwarehouse_config_map["x-small"]) ? local.sqlwarehouse_config_map["x-small"] : 1
    }
    small = {
      name             = "sql_warehouse_small_${random_string.suffix.result}"
      cluster_size     = "Small"
      max_num_clusters = can(local.sqlwarehouse_config_map["small"]) ? local.sqlwarehouse_config_map["small"] : 1
    }
    medium = {
      name             = "sql_warehouse_medium_${random_string.suffix.result}"
      cluster_size     = "Medium"
      max_num_clusters = can(local.sqlwarehouse_config_map["medium"]) ? local.sqlwarehouse_config_map["medium"] : 1
    }
    large = {
      name             = "sql_warehouse_large_${random_string.suffix.result}"
      cluster_size     = "Large"
      max_num_clusters = can(local.sqlwarehouse_config_map["large"]) ? local.sqlwarehouse_config_map["large"] : 1
    }
    x-large = {
      name             = "sql_warehouse_x_large_${random_string.suffix.result}"
      cluster_size     = "X-Large"
      max_num_clusters = can(local.sqlwarehouse_config_map["x-large"]) ? local.sqlwarehouse_config_map["x-large"] : 1
    }

    "2x-large" = {
      name             = "sql_warehouse_2x_large_${random_string.suffix.result}"
      cluster_size     = "2X-Large"
      max_num_clusters = can(local.sqlwarehouse_config_map["xx-large"]) ? local.sqlwarehouse_config_map["xx-large"] : 1
    }

    "3x-large" = {
      name             = "sql_warehouse_3x_large_${random_string.suffix.result}"
      cluster_size     = "3X-Large"
      max_num_clusters = can(local.sqlwarehouse_config_map["xxx-large"]) ? local.sqlwarehouse_config_map["xxx-large"] : 1
    }

    "4x-large" = {
      name             = "sql_warehouse_4x_large_${random_string.suffix.result}"
      cluster_size     = "4X-Large"
      max_num_clusters = can(local.sqlwarehouse_config_map["xxxx-large"]) ? local.sqlwarehouse_config_map["xxxx-large"] : 1
    }
  }

}

#cluster permission
locals {
  json_compatible_cluster_policy_permissions = (var.cluster_policy_permissions != "") ? replace(var.cluster_policy_permissions, "'", "\"") : ""
  cluster_perm_list                          = (local.json_compatible_cluster_policy_permissions != "") ? (jsondecode(local.json_compatible_cluster_policy_permissions)) : []
  cluster_policy_permissions_map = {
    for idx, config in local.cluster_perm_list : idx => config
  }
}

#pool permission
locals {
  json_compatible_pool_usage_permissions = (var.pool_usage_permissions != "") ? replace(var.pool_usage_permissions, "'", "\"") : ""
  pool_perm_list                         = (local.json_compatible_pool_usage_permissions != "") ? (jsondecode(local.json_compatible_pool_usage_permissions)) : []
  pool_usage_permissions_map = {
    for idx, config in local.pool_perm_list : idx => config
  }
}

locals {
  json_compatible_foriegn_catalog_bq_connection = (var.foriegn_catalog_bq_connection != "") ? replace(var.foriegn_catalog_bq_connection, "'", "\"") : ""
  foriegn_catalog_bq_connection_list            = (local.json_compatible_foriegn_catalog_bq_connection != "") ? (jsondecode(local.json_compatible_foriegn_catalog_bq_connection)) : []
  foriegn_catalog_bq_connection_map = {
    for idx, config in local.foriegn_catalog_bq_connection_list : idx => config
  }
}