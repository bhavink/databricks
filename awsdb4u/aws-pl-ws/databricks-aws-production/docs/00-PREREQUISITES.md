***REMOVED*** 00 - Prerequisites & System Setup

> **Before You Begin**: This guide ensures your system is properly configured for Databricks deployment.

***REMOVED******REMOVED*** Quick Reference

```
✅ Databricks Account (E2 Enterprise)
✅ Service Principal + Credentials  
✅ AWS Account + Credentials
✅ Terraform >= 1.0
✅ Environment Variables Configured
```

---

***REMOVED******REMOVED*** 1. Databricks Requirements

***REMOVED******REMOVED******REMOVED*** 1.1 Databricks Account

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
flowchart LR
    A["Databricks E2<br/>Enterprise Account"] --> B["Account Console<br/>accounts.cloud.databricks.com"]
    B --> C["Service Principal<br/>(OAuth Credentials)"]
    C --> D["Client ID"]
    C --> E["Client Secret"]
    
    style A fill:***REMOVED***FF3621,color:***REMOVED***fff
    style B fill:***REMOVED***FF9900,color:***REMOVED***fff
    style C fill:***REMOVED***569A31,color:***REMOVED***fff
```

**Required Access:**
- Databricks E2 (Enterprise) Account on AWS
- Account Admin access to `https://accounts.cloud.databricks.com`
- Ability to create Service Principals

**Docs**: [Databricks Account Console](https://docs.databricks.com/aws/en/administration-guide/account-settings-e2/index.html)

***REMOVED******REMOVED******REMOVED*** 1.2 Create Service Principal

```bash
***REMOVED*** Navigate to Account Console → User Management → Service Principals
***REMOVED*** Click "Add Service Principal"
***REMOVED*** Name: "terraform-deployment" (or your preference)
***REMOVED*** Copy the generated credentials immediately (shown only once!)
```

**Save these values** (needed for Step 4):
```
DATABRICKS_CLIENT_ID=<your-client-id>
DATABRICKS_CLIENT_SECRET=<your-client-secret>
DATABRICKS_ACCOUNT_ID=<your-account-id>
```

**Docs**: [Service Principal Setup](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m.html)

---

***REMOVED******REMOVED*** 2. AWS Requirements

***REMOVED******REMOVED******REMOVED*** 2.1 AWS Account Access

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
flowchart TD
    A["AWS Account"] --> B{Authentication Method}
    B -->|Option 1| C["AWS CLI Profile"]
    B -->|Option 2| D["AWS SSO"]
    B -->|Option 3| E["Access Keys"]
    B -->|Option 4| F["Environment Variables"]
    
    C --> G["~/.aws/credentials"]
    D --> H["aws sso login"]
    E --> I["AWS_ACCESS_KEY_ID<br/>AWS_SECRET_ACCESS_KEY"]
    F --> I
    
    style A fill:***REMOVED***FF9900,color:***REMOVED***fff
```

**Required Permissions:**
- VPC creation and management
- EC2, S3, IAM, KMS operations
- Databricks workspace deployment rights

**Verify Access:**
```bash
***REMOVED*** Test AWS authentication
aws sts get-caller-identity --profile your-profile
***REMOVED*** Output should show your AWS account ID
```

***REMOVED******REMOVED******REMOVED*** 2.2 AWS Authentication Setup

Choose ONE option:

**Option 1: Named Profile (Recommended)**
```bash
aws configure --profile databricks-deploy
***REMOVED*** AWS Access Key ID: <your-key>
***REMOVED*** AWS Secret Access Key: <your-secret>
***REMOVED*** Default region: us-west-2
***REMOVED*** Default output format: json
```

**Option 2: AWS SSO**
```bash
aws configure sso
***REMOVED*** Follow prompts to set up SSO profile
aws sso login --profile your-profile
```

**Option 3: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="<your-key>"
export AWS_SECRET_ACCESS_KEY="<your-secret>"
export AWS_DEFAULT_REGION="us-west-2"
```

**Option 4: Default Credentials**
```bash
aws configure
***REMOVED*** Uses ~/.aws/credentials [default] profile
```

---

***REMOVED******REMOVED*** 3. Required Tools

***REMOVED******REMOVED******REMOVED*** 3.1 Install Terraform

```bash
***REMOVED*** macOS (Homebrew)
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

***REMOVED*** Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

***REMOVED*** Verify
terraform --version
***REMOVED*** Required: >= 1.0.0
```

**Docs**: [Terraform Installation](https://developer.hashicorp.com/terraform/install)

***REMOVED******REMOVED******REMOVED*** 3.2 Install AWS CLI

```bash
***REMOVED*** macOS
brew install awscli

***REMOVED*** Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

***REMOVED*** Verify
aws --version
***REMOVED*** Required: >= 2.0
```

**Docs**: [AWS CLI Installation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

---

***REMOVED******REMOVED*** 4. Environment Configuration

***REMOVED******REMOVED******REMOVED*** 4.1 Terraform Provider Authentication

**Method 1: ~/.zshrc (Recommended for Security)**

```bash
***REMOVED*** Edit ~/.zshrc
nano ~/.zshrc

***REMOVED*** Add these lines (replace with your actual values)
export TF_VAR_databricks_client_id="<your-sp-client-id>"
export TF_VAR_databricks_client_secret="<your-sp-secret>"
export TF_VAR_databricks_account_id="<your-account-id>"
export TF_VAR_aws_account_id="<your-aws-account-id>"

***REMOVED*** Reload
source ~/.zshrc
```

**Method 2: .env.local File (Alternative)**

```bash
***REMOVED*** Create .env.local in project root (NEVER commit this!)
cat > .env.local << 'EOF'
export TF_VAR_databricks_client_id="<your-sp-client-id>"
export TF_VAR_databricks_client_secret="<your-sp-secret>"
export TF_VAR_databricks_account_id="<your-account-id>"
export TF_VAR_aws_account_id="<your-aws-account-id>"
EOF

***REMOVED*** Load before each session
source .env.local
```

***REMOVED******REMOVED******REMOVED*** 4.2 Verify Environment

```bash
***REMOVED*** Check Terraform variables are set
echo $TF_VAR_databricks_client_id
echo $TF_VAR_databricks_account_id

***REMOVED*** Verify AWS credentials
aws sts get-caller-identity --profile your-profile

***REMOVED*** Test Databricks authentication
curl -X GET \
  -H "Authorization: Bearer $(echo -n $TF_VAR_databricks_client_id:$TF_VAR_databricks_client_secret | base64)" \
  https://accounts.cloud.databricks.com/api/2.0/accounts/$TF_VAR_databricks_account_id/workspaces
```

---

***REMOVED******REMOVED*** 5. Pre-Flight Checklist

Run these commands to verify everything is ready:

```bash
***REMOVED*** ✅ Terraform installed
terraform --version

***REMOVED*** ✅ AWS CLI installed  
aws --version

***REMOVED*** ✅ AWS authentication works
aws sts get-caller-identity --profile your-profile

***REMOVED*** ✅ Environment variables set
echo "Client ID: ${TF_VAR_databricks_client_id:0:8}..."
echo "Account ID: $TF_VAR_databricks_account_id"

***REMOVED*** ✅ Check current directory
pwd
***REMOVED*** Should be in project root: databricks-aws-production

***REMOVED*** ✅ Verify example configuration exists
ls terraform.tfvars.example
```

**All checks passed?** → Proceed to [04-QUICK-START.md](04-QUICK-START.md)

---

***REMOVED******REMOVED*** 6. Security Best Practices

***REMOVED******REMOVED******REMOVED*** 6.1 Credential Management

```
❌ NEVER commit credentials to Git
❌ NEVER hardcode secrets in .tf files
✅ Use TF_VAR_* environment variables
✅ Store credentials in ~/.zshrc or .env.local
✅ Add sensitive files to .gitignore
```

***REMOVED******REMOVED******REMOVED*** 6.2 Files to Protect

Ensure these patterns are in `.gitignore`:
```
*.tfstate
*.tfstate.*
*.tfvars
.env
.env.*
*-key.json
*-credentials.json
*.pem
```

---

***REMOVED******REMOVED*** 7. Optional: Multi-Account Setup

If deploying to multiple AWS accounts:

```bash
***REMOVED*** ~/.aws/config
[profile account-dev]
region = us-west-2
output = json

[profile account-prod]
region = us-east-1
output = json

***REMOVED*** ~/.zshrc - Use different variables per account
export TF_VAR_aws_profile="account-dev"  ***REMOVED*** or "account-prod"
```

---

***REMOVED******REMOVED*** Next Steps

✅ Prerequisites complete → [01-ARCHITECTURE.md](01-ARCHITECTURE.md) - Understand the deployment architecture

✅ Ready to deploy → [04-QUICK-START.md](04-QUICK-START.md) - 5-minute deployment guide

---

***REMOVED******REMOVED*** Troubleshooting

| Issue | Solution |
|-------|----------|
| `terraform: command not found` | Install Terraform (see Section 3.1) |
| `aws: command not found` | Install AWS CLI (see Section 3.2) |
| `Unable to locate credentials` | Configure AWS (see Section 2.2) |
| `Environment variables not set` | Check ~/.zshrc or source .env.local (see Section 4.1) |
| `401 Unauthorized from Databricks` | Verify Service Principal credentials (see Section 1.2) |

**More Help**: See [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md)
