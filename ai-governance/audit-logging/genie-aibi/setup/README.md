# Genie Observability Setup

**Purpose:** One-time setup scripts for Genie observability infrastructure

---

## Quick Start

```bash
# 1. Create secrets (store SP credentials)
export DATABRICKS_SP_CLIENT_ID="<your-sp-client-id>"
export DATABRICKS_SP_CLIENT_SECRET="<your-sp-secret>"
python create_secrets.py

# 2. Create schema and tables
databricks sql execute -f create_schema.sql

# 3. Proceed to pipeline and ingestion setup
```

---

## Files

| File | Purpose | When to Use |
|------|---------|-------------|
| **create_secrets.py** | Creates `genie-obs` secret scope with SP credentials | **Once** - Initial setup |
| **create_schema.sql** | Creates `main.genie_analytics` schema and tables | **Once** - Initial setup |
| **cleanup_schema.sql** | Drops and recreates schema (deletes all data!) | **Rarely** - Reset/troubleshooting |

---

## 1. Create Secrets (One-Time)

### Purpose
Store service principal credentials in Databricks secrets for use by ingestion scripts.

### Prerequisites
- Service principal with Genie API access
- Databricks CLI configured (`databricks auth login`)

### Usage

```bash
cd setup/

# Set credentials in environment
export DATABRICKS_SP_CLIENT_ID="<your-sp-application-id>"
export DATABRICKS_SP_CLIENT_SECRET="<your-sp-secret>"

# Run script
python create_secrets.py

# If using non-default profile
python create_secrets.py --profile <profile-name>
```

### What it Creates
- **Secret Scope:** `genie-obs`
- **Secret Keys:**
  - `sp_client_id` - Service principal application ID
  - `sp_client_secret` - Service principal secret

### Verify

```bash
databricks secrets list-scopes
# Should show: genie-obs

databricks secrets list --scope genie-obs
# Should show: sp_client_id, sp_client_secret (values hidden)
```

---

## 2. Create Schema (One-Time)

### Purpose
Create Unity Catalog schema and tables for Genie observability data.

### Usage

```bash
databricks sql execute -f create_schema.sql
```

### What it Creates

- **Schema:** `main.genie_analytics`
- **Tables:**
  1. `message_details` - Message content & execution
  2. `message_fetch_errors` - Error tracking
  3. `genie_space_details` - Space configuration

---

## 3. Cleanup Schema (Destructive!)

### ⚠️ WARNING: Deletes All Data

```bash
databricks sql execute -f cleanup_schema.sql
```

Drops schema and all tables. Use for reset/troubleshooting only.

---

**For detailed documentation, see the full README in this directory.**
