# ============================================================================
# Databricks VPC Endpoint Service Names by AWS Region
# Source: https://docs.databricks.com/aws/en/resources/ip-domain-region#privatelink-vpc-endpoint-services
# Last Updated: 2026-01-06
# ============================================================================

locals {
  # Map of AWS regions to Databricks VPC endpoint service names
  vpce_service_names = {
    # Asia Pacific
    "ap-northeast-1" = {
      workspace = "com.amazonaws.vpce.ap-northeast-1.vpce-svc-02691fd610d24fd64"
      relay     = "com.amazonaws.vpce.ap-northeast-1.vpce-svc-02aa633bda3edbec0"
    }
    "ap-northeast-2" = {
      workspace = "com.amazonaws.vpce.ap-northeast-2.vpce-svc-0babb9bde64f34d7e"
      relay     = "com.amazonaws.vpce.ap-northeast-2.vpce-svc-0dc0e98a5800db5c4"
    }
    "ap-south-1" = {
      workspace = "com.amazonaws.vpce.ap-south-1.vpce-svc-0dbfe5d9ee18d6411"
      relay     = "com.amazonaws.vpce.ap-south-1.vpce-svc-03fd4d9b61414f3de"
    }
    "ap-southeast-1" = {
      workspace = "com.amazonaws.vpce.ap-southeast-1.vpce-svc-02535b257fc253ff4"
      relay     = "com.amazonaws.vpce.ap-southeast-1.vpce-svc-0557367c6fc1a0c5c"
    }
    "ap-southeast-2" = {
      workspace = "com.amazonaws.vpce.ap-southeast-2.vpce-svc-0b87155ddd6954974"
      relay     = "com.amazonaws.vpce.ap-southeast-2.vpce-svc-0b4a72e8f825495f6"
    }
    "ap-southeast-3" = {
      workspace = "com.amazonaws.vpce.ap-southeast-3.vpce-svc-0fec4092997affd53"
      relay     = "com.amazonaws.vpce.ap-southeast-3.vpce-svc-025ca447c232c6a1b"
    }

    # Canada
    "ca-central-1" = {
      workspace = "com.amazonaws.vpce.ca-central-1.vpce-svc-0205f197ec0e28d65"
      relay     = "com.amazonaws.vpce.ca-central-1.vpce-svc-0c4e25bdbcbfbb684"
    }

    # Europe
    "eu-central-1" = {
      workspace = "com.amazonaws.vpce.eu-central-1.vpce-svc-081f78503812597f7"
      relay     = "com.amazonaws.vpce.eu-central-1.vpce-svc-08e5dfca9572c85c4"
    }
    "eu-west-1" = {
      workspace = "com.amazonaws.vpce.eu-west-1.vpce-svc-0da6ebf1461278016"
      relay     = "com.amazonaws.vpce.eu-west-1.vpce-svc-09b4eb2bc775f4e8c"
    }
    "eu-west-2" = {
      workspace = "com.amazonaws.vpce.eu-west-2.vpce-svc-01148c7cdc1d1326c"
      relay     = "com.amazonaws.vpce.eu-west-2.vpce-svc-05279412bf5353a45"
    }
    "eu-west-3" = {
      workspace = "com.amazonaws.vpce.eu-west-3.vpce-svc-008b9368d1d011f37"
      relay     = "com.amazonaws.vpce.eu-west-3.vpce-svc-005b039dd0b5f857d"
    }

    # South America
    "sa-east-1" = {
      workspace = "com.amazonaws.vpce.sa-east-1.vpce-svc-0bafcea8cdfe11b66"
      relay     = "com.amazonaws.vpce.sa-east-1.vpce-svc-0e61564963be1b43f"
    }

    # United States Commercial
    "us-east-1" = {
      workspace = "com.amazonaws.vpce.us-east-1.vpce-svc-09143d1e626de2f04"
      relay     = "com.amazonaws.vpce.us-east-1.vpce-svc-00018a8c3ff62ffdf"
    }
    "us-east-2" = {
      workspace = "com.amazonaws.vpce.us-east-2.vpce-svc-041dc2b4d7796b8d3"
      relay     = "com.amazonaws.vpce.us-east-2.vpce-svc-090a8fab0d73e39a6"
    }
    "us-west-1" = {
      workspace = "com.amazonaws.vpce.us-west-1.vpce-svc-09bb6ca26208063f2"
      relay     = "com.amazonaws.vpce.us-west-1.vpce-svc-04cb91f9372b792fe"
    }
    "us-west-2" = {
      workspace = "com.amazonaws.vpce.us-west-2.vpce-svc-0129f463fcfbc46c5"
      relay     = "com.amazonaws.vpce.us-west-2.vpce-svc-0158114c0c730c3bb"
    }

    # AWS GovCloud
    "us-gov-west-1" = {
      workspace = "com.amazonaws.vpce.us-gov-west-1.vpce-svc-0f25e28401cbc9418"
      relay     = "com.amazonaws.vpce.us-gov-west-1.vpce-svc-05f27abef1a1a3faa"
    }

    # AWS GovCloud DoD (Note: Same region code but different endpoints)
    # To use DoD endpoints, set workspace_vpce_service and relay_vpce_service manually:
    # workspace_vpce_service = "com.amazonaws.vpce.us-gov-west-1.vpce-svc-08fddf710780b2a54"
    # relay_vpce_service     = "com.amazonaws.vpce.us-gov-west-1.vpce-svc-05c210a2feea23ad7"
  }

  # Automatically select VPC endpoint service names based on region
  # If manual override is provided via variables, use that; otherwise use the region-based lookup
  computed_workspace_vpce_service = var.workspace_vpce_service != "" ? var.workspace_vpce_service : (
    contains(keys(local.vpce_service_names), var.region) ? local.vpce_service_names[var.region].workspace : ""
  )

  computed_relay_vpce_service = var.relay_vpce_service != "" ? var.relay_vpce_service : (
    contains(keys(local.vpce_service_names), var.region) ? local.vpce_service_names[var.region].relay : ""
  )

  # Validation: Check if region is supported when VPC endpoints are enabled
  region_supported = contains(keys(local.vpce_service_names), var.region)
}
