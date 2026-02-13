# How to Get Databricks IP Ranges for Firewall Allowlisting

A short runbook for extracting Databricks IP ranges (by cloud, region, and direction) for use in firewalls and network policies. Uses the official [Databricks IP ranges](https://docs.databricks.com/security/network/ip-ranges.html) data.

---

## What you need

- **Python 3.7+** (no extra packages)
- **Network access** to `https://www.databricks.com/networking/v1/ip-ranges.json`  
  — or a **downloaded JSON file** for air-gapped use

---

## 1. Get the script

Clone or download the repo and open a terminal in the `extract-databricks-ips` folder:

```bash
cd path/to/extract-databricks-ips
```

---

## 2. Quick commands

**One cloud, CSV (default)**  
Output columns: `cloud`, `region`, `type`, `cidr`, `ipVersion`, `service`.

```bash
python extract-databricks-ips.py --cloud aws
python extract-databricks-ips.py --cloud azure
python extract-databricks-ips.py --cloud gcp
```

**One or more regions (comma-separated)**  
No `--type` = both inbound and outbound.

```bash
python extract-databricks-ips.py --cloud aws --region us-east-1
python extract-databricks-ips.py --cloud aws --region us-east-1,us-west-2,eu-west-1
```

**Egress only (outbound)**  
Use this for firewall egress allowlists.

```bash
python extract-databricks-ips.py --cloud aws --region us-east-1 --type outbound
```

**Save to a file**

```bash
python extract-databricks-ips.py --cloud aws --region us-east-1,us-west-2 --output aws-ips.csv
python extract-databricks-ips.py --cloud aws --type outbound --format simple --output aws-egress.txt
```

---

## 3. Input: URL or local file

- **Default (no flags):** Fetches the latest data from the official URL ([ip-ranges.json](https://www.databricks.com/networking/v1/ip-ranges.json)). No local copy needed.
- **Local file:** Use `--file` only when you have a downloaded or cached JSON file (e.g. air-gapped):

```bash
python extract-databricks-ips.py --file ./ip-ranges.json --cloud aws
python extract-databricks-ips.py --file https://www.databricks.com/networking/v1/ip-ranges.json --cloud aws
```

---

## 4. Output formats

| Flag           | Output |
|----------------|--------|
| *(default)*    | CSV: `cloud,region,type,cidr,ipVersion,service` |
| `--format json`| JSON array of objects |
| `--format simple` | One CIDR per line (good for scripts) |

---

## 5. Useful options

| Option | Example | Purpose |
|--------|---------|---------|
| `--cloud` | `aws`, `azure`, `gcp` | Restrict to one cloud |
| `--region` | `us-east-1` or `us-east-1,eu-west-1` | One or more regions |
| `--type` | `inbound`, `outbound` | Direction; omit for both |
| `--ipv4-only` | — | Only IPv4 CIDRs |
| `--list-regions` | `--list-regions --cloud aws` | List regions for a cloud |
| `--output` / `-o` | `--output out.csv` | Write to file |

---

## 6. End-to-end example

**Goal:** AWS outbound IPs for `us-east-1` and `us-west-2`, CSV for a firewall team.

```bash
python extract-databricks-ips.py \
  --cloud aws \
  --region us-east-1,us-west-2 \
  --type outbound \
  --output aws-egress.csv
```

Open `aws-egress.csv`; use the `cidr` column (and optionally `region`) in your firewall or automation.

---

## 7. References

- **Databricks IP ranges:** [docs.databricks.com/security/network/ip-ranges](https://docs.databricks.com/security/network/ip-ranges.html)
- **Public JSON:** `https://www.databricks.com/networking/v1/ip-ranges.json`
- **Script & full docs:** See [README.md](README.md).
