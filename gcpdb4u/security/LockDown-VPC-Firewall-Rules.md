***REMOVED*** Lock down VPC egress for Databricks on GCP 🔐

By default GCP allows egress from VPCs to any destination. To meet security and compliance requirements, you can restrict egress traffic from Databricks clusters (and other VMs) to only the essential services and destinations your organization requires.

This guide outlines recommended egress controls, firewall rule examples, and validation steps.

---

***REMOVED******REMOVED*** Key considerations
- Databricks clusters may need outbound access for:
  - Databricks control plane endpoints (region-specific NAT IPs)
  - Google APIs: Cloud Storage (`storage.googleapis.com`), Container Registry (`pkg.dev` / `gcr.io`), Artifact Registry (`*.pkg.dev`)
  - NTP, CRL/OCSP, and licensing/telemetry endpoints as required by your environment
- Prefer Private Google Access (PGA) and DNS private zones for Google APIs to avoid public internet egress.
- Test in a non-production workspace first (dry-run and monitor logs).

---

***REMOVED******REMOVED*** Recommended egress allowlist (examples)
- Databricks control plane NAT IPs (see Databricks docs for region lists)
- `199.36.153.4/30` (used for `restricted.googleapis.com` when VPC SC is in use)
- Google service ranges required by your services (e.g., `storage.googleapis.com`, `pkg.dev`, etc.)
- NTP (UDP/123), DNS (UDP/TCP/53) and any internal logging or monitoring endpoints

---

***REMOVED******REMOVED*** Example firewall rules (gcloud)
> Replace placeholders with your network, subnet, and project values.

Allow control plane IPs (egress):
```
gcloud compute firewall-rules create allow-databricks-controlplane-egress --direction=EGRESS --network=VPC_NAME --action=ALLOW --rules=tcp:443,udp:123 --destination-ranges=CONTROL_PLANE_IPS
```
Allow `restricted.googleapis.com` range (if using VPC-SC):
```
gcloud compute firewall-rules create allow-restricted-googleapis --direction=EGRESS --network=VPC_NAME --action=ALLOW --rules=tcp:443 --destination-ranges=199.36.153.4/30
```
Block all other egress by adding a deny rule with lower priority (after allowing required destinations):
```
gcloud compute firewall-rules create deny-all-egress --direction=EGRESS --network=VPC_NAME --priority=65500 --action=DENY --rules=all --destination-ranges=0.0.0.0/0
```

> Note: GCP firewall rules are stateful; ensure your allow rules are created with higher priority than the deny rule.

---

***REMOVED******REMOVED*** VPC routes & DNS
- Create private DNS zones (Cloud DNS private zones) for domains like `*.pkg.dev`, `storage.googleapis.com`, and `restricted.googleapis.com` and point them to internal/private IPs when using PGA or VPC SC.
- Ensure routes send traffic to the appropriate NAT gateway if you rely on Cloud NAT for controlled internet access.

---

***REMOVED******REMOVED*** Validation steps
1. Launch a test Databricks cluster in a non-prod workspace.
2. From the cluster (or a VM without external IP), test access to required endpoints:
```
curl -I https://storage.googleapis.com
curl -I https://restricted.googleapis.com   ***REMOVED*** if using VPC SC
```
3. Confirm no other egress is possible:
```
curl -I https://example.com  ***REMOVED*** should fail if deny-all-egress is in place
```
4. Monitor VPC Flow Logs and audit logs for dropped traffic and fine-tune allow rules.

---

***REMOVED******REMOVED*** References
- Databricks firewall guidance: https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/firewall.html
- GCP Private Google Access: https://cloud.google.com/vpc/docs/configure-private-google-access
- GCP firewall rules: https://cloud.google.com/vpc/docs/firewalls

---

**Tip**: Document your allowlist and keep it under version control to simplify audits and reviews.