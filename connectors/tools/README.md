# Tools

CLI and deployment tools for Lakeflow Community Connectors.

## community-connector CLI

The upstream [community-connector CLI](https://github.com/databrickslabs/lakeflow-community-connectors/tree/master/tools/community_connector) can be used to test and validate connectors.

### Installation

```bash
pip install community-connector
```

### Usage

```bash
# Test connector locally
community-connector test \
  --source healthcare \
  --connection-name "healthcare_test" \
  --tables patients,encounters

# Validate connector
community-connector validate \
  --source healthcare \
  --config config.yaml
```

## Deployment

See upstream documentation for deployment instructions.
