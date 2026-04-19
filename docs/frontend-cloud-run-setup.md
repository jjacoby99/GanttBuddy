# GanttBuddy Frontend Cloud Run Setup

This document captures the working setup used to deploy the Streamlit frontend to the staging GCP project and the matching GitHub Actions configuration. The production setup should follow the same flow with production-specific names and secrets.

## Architecture

The frontend is deployed as a separate Cloud Run service from the backend:

- Frontend runtime: Streamlit app in this repo
- Backend runtime: `ganttbuddy-api-*` service in the backend repo
- Auth flow:
  - Browser reaches public Cloud Run frontend URL
  - Streamlit performs Google OIDC login
  - Frontend exchanges the Google ID token with the backend at `POST /auth/oidc/exchange`
  - Backend issues the local API token used by the Streamlit frontend

## What Was Created In GCP For Staging

Project:

- Project ID: `airy-actor-492416-e0`
- Project number: `364477301326`
- Region: `us-west1`

Artifact Registry:

- Existing Docker repo reused: `ganttbuddy`

Cloud Run services:

- Frontend service: `ganttbuddy-frontend-staging`
- Backend service already existed: `ganttbuddy-api-staging`

Service accounts:

- Frontend runtime service account:
  - `ganttbuddy-frontend-staging@airy-actor-492416-e0.iam.gserviceaccount.com`
- Frontend GitHub deployer service account:
  - `gha-gb-fe-stg@airy-actor-492416-e0.iam.gserviceaccount.com`

Workload Identity Federation:

- Existing pool reused: `github-actions`
- New provider created for this repo:
  - `ganttbuddy-frontend`

Secret Manager:

- Frontend Streamlit secrets:
  - `ganttbuddy-frontend-streamlit-secrets-staging`

Google OAuth:

- Staging frontend OAuth client created in the staging GCP project
- Authorized redirect URI:
  - `https://ganttbuddy-frontend-staging-mximjolcfa-uw.a.run.app/oauth2callback`

Cloud Run access mode:

- The frontend was made browser-accessible by disabling the Cloud Run invoker IAM check:
  - `--no-invoker-iam-check`
- This was necessary because the org policy blocked `allUsers` IAM bindings

Backend staging adjustment:

- The staging backend `OIDC_CLIENT_ID` had to be updated to match the frontend Google OAuth client ID, otherwise the login looped after the Google handoff.

## What Was Created In GitHub

Repository variables used by the frontend workflow:

- `STAGING_GCP_PROJECT_ID`
- `STAGING_GCP_REGION`
- `STAGING_ARTIFACT_REGISTRY_REPOSITORY`
- `CLOUD_RUN_STAGING_FRONTEND_SERVICE`
- `CLOUD_RUN_STAGING_FRONTEND_SERVICE_ACCOUNT`
- `STAGING_GCP_WORKLOAD_IDENTITY_PROVIDER`
- `STAGING_GCP_WORKLOAD_IDENTITY_SERVICE_ACCOUNT`

Repository secrets used by the frontend workflow:

- `CLOUD_RUN_STAGING_FRONTEND_ENV_VARS`
- `CLOUD_RUN_STAGING_FRONTEND_SECRETS`

Workflow:

- `.github/workflows/frontend-ci-cd.yml`

Current branch strategy:

- `dev` auto-deploys staging
- `workflow_dispatch` is used for production deploys

## Staging Environment Variables And Secret Content

### GitHub variable values for staging

```text
STAGING_GCP_PROJECT_ID=airy-actor-492416-e0
STAGING_GCP_REGION=us-west1
STAGING_ARTIFACT_REGISTRY_REPOSITORY=ganttbuddy
CLOUD_RUN_STAGING_FRONTEND_SERVICE=ganttbuddy-frontend-staging
CLOUD_RUN_STAGING_FRONTEND_SERVICE_ACCOUNT=ganttbuddy-frontend-staging@airy-actor-492416-e0.iam.gserviceaccount.com
STAGING_GCP_WORKLOAD_IDENTITY_PROVIDER=projects/364477301326/locations/global/workloadIdentityPools/github-actions/providers/ganttbuddy-frontend
STAGING_GCP_WORKLOAD_IDENTITY_SERVICE_ACCOUNT=gha-gb-fe-stg@airy-actor-492416-e0.iam.gserviceaccount.com
```

### GitHub secret content for staging

`CLOUD_RUN_STAGING_FRONTEND_ENV_VARS`

```yaml
GANTTBUDDY_ENV: "staging"
```

`CLOUD_RUN_STAGING_FRONTEND_SECRETS`

```text
STREAMLIT_SECRETS_TOML=ganttbuddy-frontend-streamlit-secrets-staging:latest
```

### Streamlit secrets TOML shape for staging

The actual client secret and cookie secret should never be committed. This is the deployed shape:

```toml
[ganttbuddy]
environment = "staging"

[ganttbuddy.environments.staging]
api_base_url = "https://ganttbuddy-api-staging-364477301326.us-west1.run.app"
oidc_provider = "googlestaging"

[auth]
redirect_uri = "https://ganttbuddy-frontend-staging-mximjolcfa-uw.a.run.app/oauth2callback"
cookie_secret = "REPLACE_WITH_REAL_RANDOM_SECRET"
expose_tokens = "id"

[auth.googlestaging]
client_id = "REPLACE_WITH_REAL_GOOGLE_CLIENT_ID"
client_secret = "REPLACE_WITH_REAL_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

## Required Backend Alignment

The backend must validate the same Google client ID used by the Streamlit frontend. In staging, the backend environment ended up needing:

```text
AUTH_MODE=oidc
OIDC_ISSUER=https://accounts.google.com
OIDC_JWKS_URL=https://www.googleapis.com/oauth2/v3/certs
OIDC_PROVIDER_NAME=google-workspace
OIDC_CLIENT_ID=<same Google client id used in the frontend Streamlit secret>
```

If the frontend and backend `OIDC_CLIENT_ID` values diverge, Google login appears to succeed but the sign-in page just reloads because `/auth/oidc/exchange` rejects the ID token.

## Commands Used To Build Staging

### 1. Set local PowerShell variables

```powershell
$PROJECT_ID="airy-actor-492416-e0"
$PROJECT_NUMBER="364477301326"
$REGION="us-west1"

$AR_REPO="ganttbuddy"
$SERVICE_NAME="ganttbuddy-frontend-staging"

$RUNTIME_SA_NAME="ganttbuddy-frontend-staging"
$RUNTIME_SA_EMAIL="$RUNTIME_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

$DEPLOYER_SA_NAME="gha-gb-fe-stg"
$DEPLOYER_SA_EMAIL="$DEPLOYER_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

$SECRET_NAME="ganttbuddy-frontend-streamlit-secrets-staging"

$POOL_ID="github-actions"
$PROVIDER_ID="ganttbuddy-frontend"

$GITHUB_OWNER="jjacoby99"
$GITHUB_REPO="GanttBuddy"
```

### 2. Enable required APIs

```powershell
gcloud config set project $PROJECT_ID

gcloud services enable run.googleapis.com `
  artifactregistry.googleapis.com `
  secretmanager.googleapis.com `
  iam.googleapis.com `
  iamcredentials.googleapis.com
```

### 3. Create service accounts

```powershell
gcloud iam service-accounts create $RUNTIME_SA_NAME `
  --display-name="GanttBuddy Frontend Staging Runtime"

gcloud iam service-accounts create $DEPLOYER_SA_NAME `
  --display-name="GitHub Actions Frontend Staging Deployer"
```

### 4. Grant deploy permissions

```powershell
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$DEPLOYER_SA_EMAIL" `
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$DEPLOYER_SA_EMAIL" `
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$DEPLOYER_SA_EMAIL" `
  --role="roles/logging.viewer"

gcloud iam service-accounts add-iam-policy-binding $RUNTIME_SA_EMAIL `
  --member="serviceAccount:$DEPLOYER_SA_EMAIL" `
  --role="roles/iam.serviceAccountUser"
```

### 5. Create the GitHub OIDC provider

```powershell
gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID `
  --location="global" `
  --workload-identity-pool=$POOL_ID `
  --display-name="GanttBuddy Frontend GitHub" `
  --issuer-uri="https://token.actions.githubusercontent.com" `
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref" `
  --attribute-condition="assertion.repository=='$GITHUB_OWNER/$GITHUB_REPO'"

gcloud iam service-accounts add-iam-policy-binding $DEPLOYER_SA_EMAIL `
  --role="roles/iam.workloadIdentityUser" `
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/attribute.repository/$GITHUB_OWNER/$GITHUB_REPO"
```

### 6. Create the frontend Streamlit secret

```powershell
gcloud secrets create $SECRET_NAME --replication-policy="automatic"
gcloud secrets versions add $SECRET_NAME --data-file="staging-streamlit-secrets.toml"
gcloud secrets add-iam-policy-binding $SECRET_NAME `
  --member="serviceAccount:$RUNTIME_SA_EMAIL" `
  --role="roles/secretmanager.secretAccessor"
```

### 7. Set GitHub variables

```powershell
gh variable set STAGING_GCP_PROJECT_ID --body $PROJECT_ID
gh variable set STAGING_GCP_REGION --body $REGION
gh variable set STAGING_ARTIFACT_REGISTRY_REPOSITORY --body $AR_REPO
gh variable set CLOUD_RUN_STAGING_FRONTEND_SERVICE --body $SERVICE_NAME
gh variable set CLOUD_RUN_STAGING_FRONTEND_SERVICE_ACCOUNT --body $RUNTIME_SA_EMAIL
gh variable set STAGING_GCP_WORKLOAD_IDENTITY_PROVIDER --body "projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID"
gh variable set STAGING_GCP_WORKLOAD_IDENTITY_SERVICE_ACCOUNT --body $DEPLOYER_SA_EMAIL
```

### 8. Set GitHub secrets

```powershell
Get-Content .\staging-frontend-env-vars.yaml -Raw |
  gh secret set CLOUD_RUN_STAGING_FRONTEND_ENV_VARS

Get-Content .\staging-frontend-secrets.txt -Raw |
  gh secret set CLOUD_RUN_STAGING_FRONTEND_SECRETS
```

This pipe form ended up being the most reliable PowerShell pattern for uploading multiline GitHub secret content from local files.

### 9. Make the frontend browser-accessible

This is the command that actually worked under the org policy. Do not use `allUsers` bindings for this service.

```powershell
gcloud run services update ganttbuddy-frontend-staging `
  --region=us-west1 `
  --project=airy-actor-492416-e0 `
  --no-invoker-iam-check
```

### 10. Update the backend OIDC client ID to match the frontend

```powershell
gcloud run services update ganttbuddy-api-staging `
  --region=us-west1 `
  --project=airy-actor-492416-e0 `
  --update-env-vars "OIDC_CLIENT_ID=<same Google client id used by the frontend>"
```

## Manual Steps That Still Exist

These parts were not fully automated:

1. Create or update the Google OAuth web client in the target GCP project
2. Add the exact Cloud Run redirect URI:
   - `https://<frontend-service-url>/oauth2callback`
3. Copy the real client ID and client secret into the Streamlit TOML secret
4. Publish a new Secret Manager version
5. Redeploy the frontend
6. Keep the backend `OIDC_CLIENT_ID` aligned with the frontend Google client ID

If you need to update a backend repo secret from a local file, use the same pipe pattern. For example:

```powershell
Get-Content .\staging-backend-env-vars.yaml -Raw |
  gh secret set CLOUD_RUN_STAGING_ENV_VARS --repo jjacoby99/ganttbuddy-api
```

## Production Checklist

For production, repeat the same flow with production-specific values:

- project id / number
- runtime service account
- deployer service account
- Cloud Run service name
- Secret Manager secret name
- GitHub variables and secrets
- Google OAuth client
- backend `OIDC_CLIENT_ID`

Recommended production naming:

- service: `ganttbuddy-frontend-production`
- runtime SA: `ganttbuddy-frontend-production@<project>.iam.gserviceaccount.com`
- deployer SA: keep under 30 chars, for example `gha-gb-fe-prod`
- secret: `ganttbuddy-frontend-streamlit-secrets-production`

## Common Failure Modes We Hit

1. Missing packages in `requirements.txt`
   - `dataclasses-json`
   - `openpyxl`
   - `pydantic`
   - `streamlit-plotly-events2`

2. Public access via `allUsers` was blocked by org policy
   - fix was `--no-invoker-iam-check`

3. Frontend container failed to start on Cloud Run
   - root cause was `/app` not writable by the non-root runtime user
   - fixed in `Dockerfile` by creating `/app/.streamlit` and chowning `/app`

4. Google login looped back to sign-in
   - root cause was backend `OIDC_CLIENT_ID` not matching the frontend Google client ID

5. OAuth 400 `invalid_request`
   - root cause was still using the placeholder redirect URI in the deployed secret

6. TLS/HSTS error on another computer
   - root cause was a mistyped Cloud Run hostname (`...-uw-a.run.app` instead of `...-uw.a.run.app`)

## Recommended Future Improvement

The frontend and backend should share one clear source of truth for the Google client ID used in each environment. Otherwise the frontend and backend can drift and break login.

At minimum:

- document the staging and production Google OAuth client IDs
- update the backend deploy config so it does not revert the OIDC client ID on redeploy
- keep the frontend Streamlit secret and backend OIDC config in sync per environment
