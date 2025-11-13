# Azure authentication (interactive & CI)

This short guide shows the minimal steps to authenticate local development and CI for the Change_Management project.

## Environment variables (fill locally, do NOT commit)

Copy `src/config/.env.example` to `src/.env` and fill values locally. Key variables used by the project:

- PROJECT_ENDPOINT=   # your Azure AI / Foundry endpoint (https://...)
- AGENT_MODEL_DEPLOYMENT_NAME=

Service-principal variables (required for CI/non-interactive runs):

- AZURE_CLIENT_ID=
- AZURE_TENANT_ID=
- AZURE_CLIENT_SECRET=

## Local developer (interactive)

1. Install the Azure CLI on your machine or devcontainer (not via pip):

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

2. Log in interactively:

```bash
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

3. Run the example auth checker to verify credentials:

```bash
/workspaces/Change_Management/venv/bin/python src/examples/example_auth.py
```

If Azure CLI credentials are available, `DefaultAzureCredential` will pick them up and the script will acquire a token.

## CI / non-interactive (service principal)

1. Create a service principal (least privilege recommended):

```bash
az ad sp create-for-rbac --name "change-mgmt-sp" \
  --role "Contributor" \
  --scopes /subscriptions/<SUB_ID>/resourceGroups/<RG_NAME> \
  --sdk-auth
```

2. Store the returned credentials securely in your CI (GitHub Actions secrets, Azure DevOps variable group, etc.). Set at least:

- AZURE_CLIENT_ID
- AZURE_TENANT_ID
- AZURE_CLIENT_SECRET
- PROJECT_ENDPOINT

3. In GitHub Actions you can either export those secrets as env vars or use `azure/login` action with the `AZURE_CREDENTIALS` JSON.

Example job snippet for GitHub Actions:

```yaml
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install deps
        run: pip install -r requirement.txt
      - name: Run auth check
        env:
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
          PROJECT_ENDPOINT: ${{ secrets.PROJECT_ENDPOINT }}
        run: python src/examples/example_auth.py
```

## Notes

- Do NOT add `azure-cli` to `requirement.txt`. The Azure CLI is a separate system tool.
- Add `python-dotenv`, `azure-identity`, and the specific Azure AI SDK for your product to `requirement.txt`.
- Prefer Managed Identity in production when running on Azure resources (VMs, App Service, AKS) to avoid storing client secrets.

If you'd like, I can also add a short paragraph to the main `README.md` linking to this file.