# Databricks GCE Compute Migration

## Overview

This folder contains policies and documentation for the **Databricks GCE (Compute Engine) migration** - the transition from GKE-based (Kubernetes) to GCE-based (Compute Engine) classic compute clusters.

## What is the GCE Migration?

Databricks is migrating the underlying infrastructure for classic compute clusters:
- **FROM**: GKE-based (Google Kubernetes Engine) clusters
- **TO**: GCE-based (Compute Engine) clusters
- **WHY**: Improved performance, reliability, and simplified architecture
- **WHEN**: Announced migration - check Databricks documentation for timeline

## What's in This Folder

### cmv1-gce-policy.yaml

**Purpose**: Policy to allow Databricks to create/update firewall rules in customer-managed VPCs during the GCE migration.

**Type**: IAM conditional policy or org policy constraint (NOT a VPC Service Controls policy)

**When Needed**:
- ✅ During GCE migration for customer-managed VPCs
- ✅ If you want Databricks to automatically create firewall rules
- ❌ NOT needed if you manually pre-create the firewall rule

## Do You Need This?

### ✅ You NEED this migration if:
- You use **customer-managed VPCs** (Shared VPC or standalone VPC)
- You have **classic compute** Databricks workspaces
- You received notification about the GCE migration from Databricks

### ❌ You DON'T need this if:
- You use **Databricks-managed VPCs**
- You only use **serverless compute** (no classic clusters)
- You already completed the migration

## Required Firewall Rule

The GCE migration requires a new firewall rule to allow the `delegate-sa` service account to manage cluster instances:

### Firewall Rule Specifications

| Property | Value |
|----------|-------|
| **Rule Name** | `databricks-cmv1-worker-to-worker-gce` |
| **Direction** | INGRESS |
| **Action** | ALLOW |
| **Protocols** | All (tcp, udp, icmp) |
| **Source** | `delegate-sa@prod-gcp-[REGION].iam.gserviceaccount.com` |
| **Target** | All workspace subnets (or databricks-worker tagged instances) |
| **Priority** | 1000 |
| **Purpose** | Allow delegate-sa to launch and manage GCE cluster instances |

## Implementation Options

### Option 1: Manual Firewall Rule Creation (RECOMMENDED)

Create the firewall rule manually before migration. This is the **recommended approach**.

**Command**:
```bash
gcloud compute firewall-rules create databricks-cmv1-worker-to-worker-gce \
  --network=VPC_NAME \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=all \
  --source-service-accounts=delegate-sa@prod-gcp-[REGION].iam.gserviceaccount.com \
  --target-tags=databricks-worker \
  --priority=1000 \
  --description="Databricks GCE migration - allow delegate-sa to manage cluster instances"
```

**Replace**:
- `VPC_NAME`: Your VPC network name
- `[REGION]`: Your Databricks region (e.g., `us-east1`, `us-central1`)

**Advantages**:
- ✅ Full control over firewall rule
- ✅ No additional policy required
- ✅ Can customize rule parameters
- ✅ Rule persists after migration

### Option 2: Let Databricks Create the Rule (USE POLICY FILE)

Use the `cmv1-gce-policy.yaml` to allow Databricks to automatically create the firewall rule.

**Steps**:

1. **Update cmv1-gce-policy.yaml**:
   ```yaml
   principalEmail: "your-admin@corp.com"
   source: "projects/YOUR_DATABRICKS_CP_PROJECT"
   targetResource: "projects/YOUR_CUSTOMER_VPC_PROJECT"
   ```

2. **Apply the policy** (method depends on your org structure):
   - As IAM conditional policy on VPC project
   - As organization policy constraint
   - Consult with your GCP administrator

3. **Coordinate with Databricks** support for migration timing

4. **Remove policy** after migration is complete

**Advantages**:
- ✅ Automated by Databricks
- ✅ Less manual work

**Disadvantages**:
- ❌ Requires additional IAM policy
- ❌ Temporary permission grant to Databricks
- ❌ Less control over rule parameters

## Migration Workflow

### Pre-Migration

```mermaid
graph TD
    A[Start] --> B{Customer-Managed VPC?}
    B -->|Yes| C[Firewall Rule Needed]
    B -->|No| D[No Action Needed]

    C --> E{Choose Implementation}
    E -->|Manual| F[Create Firewall Rule Manually]
    E -->|Automatic| G[Apply cmv1-gce-policy.yaml]

    F --> H[Verify Rule Created]
    G --> I[Coordinate with Databricks]

    H --> J[Ready for Migration]
    I --> J
    D --> J

    style F fill:"#90EE90"
    style G fill:"#FFE6B3"
    style J fill:"#87CEEB"
```

### During Migration

1. **Databricks initiates migration** for your workspace
2. **Delegate-sa uses firewall rule** to launch GCE instances
3. **Classic clusters transition** from GKE to GCE infrastructure
4. **Monitor cluster health** during transition
5. **Verify clusters function** correctly on GCE

### Post-Migration

1. **Verify all clusters operational** on GCE infrastructure
2. **Remove cmv1-gce-policy.yaml** (if used Option 2)
3. **Keep firewall rule** (required for ongoing operations)
4. **Update documentation** to reflect GCE architecture

## What is delegate-sa?

**Service Account**: `delegate-sa@prod-gcp-[GEO]-[REGION].iam.gserviceaccount.com`

**Purpose**: Databricks regional service account that launches and manages GCE-based cluster instances.

**Examples by Region**:
| Region | Delegate SA |
|--------|-------------|
| us-east1 | `delegate-sa@prod-gcp-us-east1.iam.gserviceaccount.com` |
| us-central1 | `delegate-sa@prod-gcp-us-central1.iam.gserviceaccount.com` |
| us-east4 | `delegate-sa@prod-gcp-us-east4.iam.gserviceaccount.com` |
| europe-west2 | `delegate-sa@prod-gcp-europe-west2.iam.gserviceaccount.com` |

**Find Yours**: [Databricks Regional Resources](https://docs.databricks.com/gcp/en/resources/ip-domain-region)

## Verification

After creating the firewall rule, verify it's configured correctly:

```bash
# List firewall rules
gcloud compute firewall-rules list --filter="name:databricks-cmv1"

# Describe the rule
gcloud compute firewall-rules describe databricks-cmv1-worker-to-worker-gce

# Expected output should show:
# - Direction: INGRESS
# - Allowed: all protocols
# - Source service accounts: delegate-sa@prod-gcp-[REGION].iam.gserviceaccount.com
# - Target tags: databricks-worker (or target subnet)
```

## Troubleshooting

### Migration Fails with Permission Errors

**Symptom**: Cluster launch fails with "insufficient permissions" error

**Causes**:
- Firewall rule not created or misconfigured
- delegate-sa missing required permissions
- Wrong source project in policy

**Solutions**:
1. Verify firewall rule exists: `gcloud compute firewall-rules list`
2. Check delegate-sa has compute.instances.create permission
3. Review GCP audit logs for specific denial
4. Ensure VPC-SC perimeter (if configured) allows delegate-sa

### Firewall Rule Creation Fails

**Symptom**: Rule creation command fails

**Causes**:
- VPC network name incorrect
- Conflicting rule with same name exists
- compute.googleapis.com API not enabled

**Solutions**:
1. Verify VPC network name: `gcloud compute networks list`
2. Check for existing rule: `gcloud compute firewall-rules list --filter="name:databricks-cmv1"`
3. Enable Compute API: `gcloud services enable compute.googleapis.com`

### Clusters Stuck in PENDING State

**Symptom**: After migration, clusters don't start

**Causes**:
- Firewall rule not allowing traffic
- delegate-sa blocked by VPC-SC
- Subnet IP space exhausted

**Solutions**:
1. Verify firewall rule: `gcloud compute firewall-rules describe databricks-cmv1-worker-to-worker-gce`
2. Check VPC-SC egress rules include delegate-sa
3. Review subnet IP availability
4. Check Databricks cluster event logs

## Important Notes

### ⚠️ This is NOT a VPC Service Controls Policy

The `cmv1-gce-policy.yaml` file is **NOT** a VPC Service Controls (VPC-SC) policy. It's an **IAM conditional policy** or **org policy constraint**.

**Don't confuse with**:
- VPC-SC ingress/egress policies (in `/templates/vpcsc-policy/`)
- VPC firewall rules (in `/templates/firewall-rules/` or managed by gcloud)

### ⚠️ Keep the Firewall Rule After Migration

The `databricks-cmv1-worker-to-worker-gce` firewall rule is **required for ongoing operations**, not just migration:
- ✅ Keep the rule permanently
- ❌ Do NOT delete after migration
- ✅ Required for all future cluster launches

Only the **policy file** (cmv1-gce-policy.yaml) should be removed after migration if you used Option 2.

### ⚠️ Region-Specific Configuration

Each region has its own delegate-sa. If you have workspaces in multiple regions:
- Create firewall rule per region with correct delegate-sa
- Or use a single rule with multiple source service accounts

## Integration with Other Security Controls

### VPC Service Controls

If you use VPC-SC, ensure your egress policies allow delegate-sa:

**Required in egress.yaml**:
```yaml
- egressFrom:
    identities:
    - serviceAccount:delegate-sa@prod-gcp-[REGION].iam.gserviceaccount.com
  egressTo:
    operations:
      - serviceName: compute.googleapis.com
    resources:
      - projects/[DATABRICKS_CONTROL_PLANE_PROJECT]
```

See: `/templates/vpcsc-policy/egress.yaml`

### VPC Firewall Rules

The GCE migration firewall rule works alongside other Databricks firewall rules:
- Intra-cluster communication rules
- Control plane connectivity rules
- Private Google Access egress rules

See: `/security/LockDown-VPC-Firewall-Rules.md`

## FAQ

**Q: Do I need this for Databricks-managed VPCs?**
A: No, Databricks handles this automatically for managed VPCs.

**Q: When will the migration happen?**
A: Check Databricks documentation and your account notifications for timeline.

**Q: Can I opt-out of the migration?**
A: No, the GCE migration is mandatory for all classic compute workspaces.

**Q: Will this affect my running clusters?**
A: Existing clusters continue running. New clusters use GCE infrastructure after migration.

**Q: Do I need to update my notebooks or code?**
A: No, the migration is transparent to user code.

**Q: What about serverless compute?**
A: Serverless is unaffected - already uses different infrastructure.

**Q: How long does migration take?**
A: Per-workspace migration is typically quick, but coordinate with Databricks for exact timing.

## Support and Resources

### Databricks Documentation

- **GCE Migration Announcement**: https://docs.databricks.com/gcp/en/admin/cloud-configurations/gcp/gce-update
- **Customer-Managed VPC Requirements**: https://docs.databricks.com/gcp/en/admin/cloud-configurations/gcp/gce-update#updates-needed-for-customer-managed-vpcs
- **Regional Resources**: https://docs.databricks.com/gcp/en/resources/ip-domain-region

### Related Documentation

- **VPC Service Controls Setup**: `/security/Configure-VPC-SC.md`
- **Firewall Rules**: `/security/LockDown-VPC-Firewall-Rules.md`
- **VPC-SC Egress Policies**: `/templates/vpcsc-policy/egress.yaml`

### Getting Help

- **Databricks Support**: Open ticket at https://help.databricks.com
- **Account Team**: Contact your Databricks Account Executive
- **GCP Support**: For GCP-specific firewall/IAM issues

---

## Quick Reference

### Manual Firewall Rule Creation (Recommended)

```bash
gcloud compute firewall-rules create databricks-cmv1-worker-to-worker-gce \
  --network=VPC_NAME \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=all \
  --source-service-accounts=delegate-sa@prod-gcp-REGION.iam.gserviceaccount.com \
  --target-tags=databricks-worker \
  --priority=1000
```

### Verification Command

```bash
gcloud compute firewall-rules describe databricks-cmv1-worker-to-worker-gce
```

### Find Your delegate-sa

```bash
# From Databricks documentation based on your region
# Format: delegate-sa@prod-gcp-[REGION].iam.gserviceaccount.com
```

---

**Summary**: The GCE migration requires a new firewall rule for delegate-sa. Create it manually (recommended) or use the policy file to let Databricks create it automatically. Keep the firewall rule permanently but remove the policy after migration.
