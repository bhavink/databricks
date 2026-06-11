# Legacy VPC-SC Policies (GKE-based classic compute)

> ⚠️ **DEPRECATED — historical reference only.** These VPC Service Controls ingress/egress
> policies were written for the **GKE-based** classic compute plane, which has been retired.
> All classic compute on GCP now runs on **GCE (Compute Engine)**. They are kept here only for
> historical context and to help interpret perimeters that predate the GCE migration.

## Do not use for new deployments

For current GCE-based workspaces, use the policies in the parent directory:

| Use this (current, GCE-based) | Instead of (legacy, GKE-based) |
|---|---|
| `../ingress.yaml` | `ingress.yaml` |
| `../egress.yaml` | `egress.yaml` |
| `../create-ws-ingress.yaml` | `create-ws-ingress.yaml` |
| `../create-ws-ingress.yaml` (egress folded into `../egress.yaml`) | `create-ws-egress.yaml` |

What makes these policies legacy: `ingress.yaml` permits the **Kubernetes Engine API**
(`container.googleapis.com`), which the GCE-based compute plane no longer uses. The GKE-era
service accounts these perimeters were built around (`cluster-manager-k8s-sa`,
`us-central1-gar-access`) are likewise retired. See `../../../security/Configure-VPC-SC.md` for the
current identity and service-account reference.
