***REMOVED*** Least Privilege Workspaces (LPW) VPC-SC Policies

***REMOVED******REMOVED*** Overview

This folder contains VPC Service Controls policies for **Least Privilege Workspaces (LPW)** - a special, highly restricted Databricks workspace configuration that requires explicit allowlisting.

***REMOVED******REMOVED*** What are Least Privilege Workspaces?

Least Privilege Workspaces are Databricks deployments with:
- **Extremely restrictive security posture**: Maximum security lockdown
- **Explicit allowlisting required**: Every access pattern must be pre-approved by Databricks
- **Special use case**: Not a common deployment pattern
- **Custom configuration**: Tailored to specific security/compliance requirements

***REMOVED******REMOVED*** When to Use LPW Policies

Use Least Privilege Workspace policies when:
- ✅ Your organization requires the highest level of security controls
- ✅ You need explicit allowlisting of all traffic patterns
- ✅ Regulatory requirements mandate defense-in-depth with explicit approvals
- ✅ You've coordinated with Databricks support for LPW setup
- ❌ **NOT for standard deployments** - use the regular policies instead

***REMOVED******REMOVED*** Key Differences from Standard Policies

| Aspect | Standard Workspaces | Least Privilege Workspaces (LPW) |
|--------|---------------------|----------------------------------|
| **Security Posture** | Secure (recommended for most) | Maximum security (explicit allowlist) |
| **Setup Complexity** | Standard | High - requires Databricks approval |
| **VPC-SC Rules** | Comprehensive but flexible | Extremely restrictive |
| **Use Cases** | Most production deployments | Highly regulated environments |
| **Support** | Self-service | Requires Databricks engagement |

***REMOVED******REMOVED*** Files in This Folder

***REMOVED******REMOVED******REMOVED*** create-ws-lpw.yaml

VPC-SC policy for creating Least Privilege Workspaces during workspace creation phase.

**Key characteristics**:
- More restrictive than standard create-ws-ingress.yaml
- Requires explicit Databricks allowlisting
- Custom rules tailored to LPW requirements
- Must be coordinated with Databricks support

***REMOVED******REMOVED*** How to Use LPW Policies

***REMOVED******REMOVED******REMOVED*** Prerequisites

1. **Databricks Support Engagement**:
   - Contact Databricks support to request LPW setup
   - Provide your security requirements and compliance needs
   - Receive approval and configuration guidance from Databricks

2. **Security Requirements Documentation**:
   - Document your specific security constraints
   - List compliance frameworks you must meet (SOC 2, HIPAA, FedRAMP, etc.)
   - Identify data classification levels and handling requirements

3. **Technical Prerequisites**:
   - VPC Service Controls configured and operational
   - Private Google Access with `restricted.googleapis.com`
   - VPC firewall rules following deny-by-default approach
   - Access Context Manager policies defined

***REMOVED******REMOVED******REMOVED*** Setup Process

1. **Coordinate with Databricks**:
   ```
   - Engage Databricks support team
   - Share security requirements
   - Receive LPW-specific configuration guidance
   - Get approval for deployment
   ```

2. **Review and Customize Policies**:
   ```
   - Review create-ws-lpw.yaml
   - Update with your project numbers and identities
   - Validate against your security requirements
   - Test in dry-run mode
   ```

3. **Deploy LPW Policies**:
   ```bash
   ***REMOVED*** Create Access Context Manager Access Level
   gcloud access-context-manager levels create databricks_lpw_access \
     --basic-level-spec=lpw-access-level.yaml \
     --policy=$ACCESS_POLICY_ID

   ***REMOVED*** Create VPC-SC Perimeter with LPW policy (dry-run first)
   gcloud access-context-manager perimeters dry-run create databricks-lpw-perimeter \
     --title="Databricks LPW Perimeter" \
     --resources=projects/$PROJECT_NUMBER \
     --ingress-policies=create-ws-lpw.yaml \
     --policy=$ACCESS_POLICY_ID

   ***REMOVED*** Test in dry-run mode
   ***REMOVED*** Monitor logs for violations

   ***REMOVED*** Enforce after validation
   gcloud access-context-manager perimeters dry-run enforce databricks-lpw-perimeter \
     --policy=$ACCESS_POLICY_ID
   ```

4. **Create Workspace**:
   ```
   - Create Databricks workspace using UI or API
   - Monitor workspace creation closely
   - Validate all resources created successfully
   - Test cluster launch and basic operations
   ```

5. **Post-Creation Configuration**:
   ```
   - After workspace creation, update to operational LPW policies
   - Add egress rules specific to your LPW requirements
   - Continue monitoring VPC-SC logs
   - Coordinate any policy adjustments with Databricks support
   ```

***REMOVED******REMOVED*** Important Notes

***REMOVED******REMOVED******REMOVED*** Not a Self-Service Feature

⚠️ **WARNING**: Least Privilege Workspaces require Databricks support engagement:
- Cannot be deployed without Databricks approval
- Requires custom configuration per deployment
- Not covered by standard Databricks documentation
- Ongoing support coordination may be needed

***REMOVED******REMOVED******REMOVED*** Testing Requirements

Before production deployment:
1. **Dry-Run Testing**: Always test policies in dry-run mode first
2. **Non-Production Validation**: Create test workspace in dev/test environment
3. **Log Monitoring**: Continuously monitor VPC-SC audit logs
4. **Databricks Validation**: Have Databricks support review your configuration

***REMOVED******REMOVED******REMOVED*** Maintenance

LPW deployments require ongoing maintenance:
- Regular review of VPC-SC policies
- Updates when Databricks changes service architecture
- Coordination with Databricks for Databricks-side changes
- Quarterly security audits of access patterns

***REMOVED******REMOVED*** Troubleshooting

***REMOVED******REMOVED******REMOVED*** Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Workspace creation fails | LPW policy too restrictive | Review VPC-SC logs, coordinate with Databricks support |
| Cluster launch fails | Missing egress rules for runtime images | Add required egress rules with Databricks guidance |
| Access denied errors | Insufficient permissions in LPW policy | Review and expand policy with Databricks approval |
| Policy conflicts | LPW policy incompatible with VPC-SC setup | Align policies with Databricks LPW requirements |

***REMOVED******REMOVED******REMOVED*** Debug Commands

```bash
***REMOVED*** Check VPC-SC violations specific to LPW perimeter
gcloud logging read "protoPayload.metadata.@type=type.googleapis.com/google.cloud.audit.VpcServiceControlAuditMetadata AND protoPayload.metadata.securityPolicyInfo.servicePerimeterName:databricks-lpw-perimeter" \
  --limit=50 \
  --format=json

***REMOVED*** Describe LPW perimeter
gcloud access-context-manager perimeters describe databricks-lpw-perimeter \
  --policy=$ACCESS_POLICY_ID

***REMOVED*** List access levels for LPW
gcloud access-context-manager levels list \
  --policy=$ACCESS_POLICY_ID \
  --filter="name:lpw"
```

***REMOVED******REMOVED*** Comparison: Standard vs LPW Policies

***REMOVED******REMOVED******REMOVED*** Standard Policies (Regular Workspaces)

Located in: `/templates/vpcsc-policy/`

**Files**:
- `create-ws-ingress.yaml` - Workspace creation ingress
- `ingress.yaml` - Operational ingress
- `egress.yaml` - Operational egress

**Use when**: Most production deployments

***REMOVED******REMOVED******REMOVED*** LPW Policies (This Folder)

Located in: `/templates/vpcsc-policy/least-privilege-workspaces/`

**Files**:
- `create-ws-lpw.yaml` - LPW workspace creation
- (Additional operational policies as provided by Databricks)

**Use when**: Maximum security, explicit allowlisting required

***REMOVED******REMOVED*** Migration Path

***REMOVED******REMOVED******REMOVED*** From Standard to LPW

If you need to migrate from standard to LPW:

1. **Contact Databricks Support**: Required for LPW enablement
2. **Review Current Setup**: Document existing policies and configurations
3. **Plan Migration**: Work with Databricks to plan migration approach
4. **Test in Parallel**: Create new LPW workspace, don't migrate existing
5. **Gradual Transition**: Move workloads incrementally after validation

***REMOVED******REMOVED******REMOVED*** From LPW to Standard

Not recommended - typically LPW is used for compliance reasons that persist.

***REMOVED******REMOVED*** Support and Resources

***REMOVED******REMOVED******REMOVED*** Databricks Support

For LPW deployments, always engage Databricks support:
- **Databricks Support Portal**: https://help.databricks.com
- **Account Team**: Contact your Databricks Account Executive
- **Professional Services**: Consider Databricks PS engagement for complex LPW setups

***REMOVED******REMOVED******REMOVED*** Documentation

- Standard VPC-SC Setup: `../Configure-VPC-SC.md`
- Private Google Access: `../Configure-PrivateGoogleAccess.md`
- Firewall Rules: `../LockDown-VPC-Firewall-Rules.md`
- Databricks VPC-SC Docs: https://docs.gcp.databricks.com/en/security/network/vpc-sc.html

---

***REMOVED******REMOVED*** Summary

Least Privilege Workspaces provide maximum security for Databricks deployments but require:
- ✅ Databricks support engagement and approval
- ✅ Explicit allowlisting of all access patterns
- ✅ Higher operational complexity
- ✅ Ongoing coordination with Databricks

**For most deployments, use the standard VPC-SC policies in the parent folder instead.**

Only use LPW policies when you have specific regulatory requirements that mandate this level of security and have received approval from Databricks support.
