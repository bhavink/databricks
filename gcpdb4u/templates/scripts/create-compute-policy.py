import requests
import json

# Replace these with your Databricks instance URL and personal access token
DATABRICKS_INSTANCE = 'https://<your-databricks-workspace-url>'
# ex: https://123456789108.8.gcp.databricks.com
DATABRICKS_TOKEN = 'https://<your-databricks-token>'
# ex: https://docs.gcp.databricks.com/en/dev-tools/auth/pat.html

# Set up the request headers
headers = {
    'Authorization': f'Bearer {DATABRICKS_TOKEN}',
    'Content-Type': 'application/json'
}

def create_policy(policy_name, description, definition):
    policy_json = {
        "name": policy_name,
        "description": description,
        "definition": json.dumps(definition)
    }
    
    response = requests.post(
        f'{DATABRICKS_INSTANCE}/api/2.0/policies/clusters/create',
        headers=headers,
        data=json.dumps(policy_json)
    )
    
    if response.status_code == 200:
        print(f"Policy '{policy_name}' created successfully")
    else:
        print(f"Failed to create policy '{policy_name}': {response.text}")

def list_policies(policy_name):
    response = requests.get(
        f'{DATABRICKS_INSTANCE}/api/2.0/policies/clusters/list',
        headers=headers
    )
    
    if response.status_code == 200:
        policies = response.json().get('policies', [])
        created_policy = next((policy for policy in policies if policy['name'] == policy_name), None)
        
        if created_policy:
            print(f"Policy '{policy_name}' found:")
            print(json.dumps(created_policy, indent=4))
        else:
            print(f"Policy '{policy_name}' not found.")
    else:
        print(f"Failed to list policies: {response.text}")

# Example usage
policy_definitions = [
    {
        "name": "n2-highmem-4-reservation-policy",
        "description": "Compute policy to use reservations",
        "definition": {
            "gcp_attributes.zone_id": {
                "type": "fixed",
                "value": "us-central1-c"
            },
            "gcp_attributes.local_ssd_count": {
                "type": "fixed",
                "value": 1
            },
            "node_type_id": {
                "type": "regex",
                "pattern": "n2-highmem-4",
                "hidden": False
            },
            "driver_node_type_id": {
                "type": "fixed",
                "value": "n2-highmem-4",
                "hidden": True
            }
        }
    },
    {
        "name": "n2d-highmem-8-reservation-policy",
        "description": "Compute policy to use reservations",
        "definition": {
            "gcp_attributes.zone_id": {
                "type": "fixed",
                "value": "us-central1-c"
            },
            "gcp_attributes.local_ssd_count": {
                "type": "fixed",
                "value": 2
            },
            "node_type_id": {
                "type": "regex",
                "pattern": "n2d-highmem-8",
                "hidden": False
            },
            "driver_node_type_id": {
                "type": "fixed",
                "value": "n2d-highmem-8",
                "hidden": True
            }
        }
    }
]

for policy in policy_definitions:
    create_policy(policy['name'], policy['description'], policy['definition'])
    list_policies(policy['name'])
