"""Example auth checker for Azure DefaultAzureCredential.

Usage:
  - Fill `src/.env` (or use `az login` locally).
  - Run this script to verify a token can be acquired.

This script tries two common scopes and prints a short success message.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv("src/.env")

PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT")
if not PROJECT_ENDPOINT:
    print("PROJECT_ENDPOINT not set in src/.env (or environment). Please set it and retry.")
    sys.exit(2)

try:
    from azure.identity import DefaultAzureCredential
except Exception as exc:
    print("Missing dependency 'azure-identity' or import error:", exc)
    print("Install dependencies: pip install python-dotenv azure-identity")
    sys.exit(3)

cred = DefaultAzureCredential()

# Try common scopes. Adjust if your product needs a different scope.
scopes = [
    "https://management.azure.com/.default",
    "https://cognitiveservices.azure.com/.default",
]

for scope in scopes:
    try:
        token = cred.get_token(scope)
        print(f"Successfully acquired token for scope {scope}. Expires at: {token.expires_on}")
        print("You are authenticated. DefaultAzureCredential will pick up az login or service principal env vars.")
        sys.exit(0)
    except Exception as e:
        # keep trying other scopes
        last_err = e

print("Failed to acquire token for tried scopes. Last error:", str(last_err))
print("If running locally, run: az login")
print("For CI, set AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET in your environment or secrets.")
sys.exit(4)
