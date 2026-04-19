[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [string]$ProjectNumber,

    [Parameter(Mandatory = $true)]
    [string]$Region,

    [Parameter(Mandatory = $true)]
    [string]$ArtifactRegistryRepository,

    [Parameter(Mandatory = $true)]
    [string]$ServiceName,

    [Parameter(Mandatory = $true)]
    [string]$RuntimeServiceAccountName,

    [Parameter(Mandatory = $true)]
    [string]$DeployerServiceAccountName,

    [Parameter(Mandatory = $true)]
    [string]$SecretName,

    [Parameter(Mandatory = $true)]
    [string]$PoolId,

    [Parameter(Mandatory = $true)]
    [string]$ProviderId,

    [Parameter(Mandatory = $true)]
    [string]$GithubOwner,

    [Parameter(Mandatory = $true)]
    [string]$GithubRepo,

    [Parameter(Mandatory = $true)]
    [string]$GithubEnvironmentPrefix,

    [Parameter(Mandatory = $false)]
    [string]$SecretsTomlPath,

    [switch]$CreateGithubVariables,

    [switch]$CreateGithubSecrets
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-GcloudCommandPath {
    $cmd = Get-Command gcloud.cmd -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $defaultCmd = Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    if (Test-Path $defaultCmd) {
        return $defaultCmd
    }

    throw "Unable to locate gcloud.cmd. Ensure the Google Cloud SDK is installed and on PATH."
}

$GcloudCmdPath = Get-GcloudCommandPath

function Invoke-GcloudCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process `
            -FilePath $GcloudCmdPath `
            -ArgumentList $Arguments `
            -NoNewWindow `
            -Wait `
            -PassThru `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath

        $stdout = if (Test-Path $stdoutPath) { Get-Content $stdoutPath -Raw } else { "" }
        $stderr = if (Test-Path $stderrPath) { Get-Content $stderrPath -Raw } else { "" }
        $combined = @($stdout, $stderr) | Where-Object { $_ } 

        return [pscustomobject]@{
            Output = $combined
            ExitCode = $process.ExitCode
            Text = ($combined -join [Environment]::NewLine)
        }
    } finally {
        Remove-Item $stdoutPath, $stderrPath -ErrorAction SilentlyContinue
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "==> $Message"
    & $Action
}

function Ensure-Secret {
    param(
        [string]$Name
    )

    $result = Invoke-GcloudCapture -Arguments @("secrets", "describe", $Name, "--project", $ProjectId)
    if ($result.ExitCode -eq 0) {
        Write-Host "Secret '$Name' already exists."
        return
    }

    if ($result.Text -notmatch "NOT_FOUND") {
        throw "Failed checking secret '$Name': $($result.Text)"
    }

    gcloud secrets create $Name --replication-policy automatic --project $ProjectId
}

function Ensure-ServiceAccount {
    param(
        [string]$Name,
        [string]$DisplayName
    )

    $email = "$Name@$ProjectId.iam.gserviceaccount.com"
    $result = Invoke-GcloudCapture -Arguments @("iam", "service-accounts", "describe", $email, "--project", $ProjectId)
    if ($result.ExitCode -eq 0) {
        Write-Host "Service account '$email' already exists."
        return $email
    }

    if ($result.Text -notmatch "NOT_FOUND") {
        throw "Failed checking service account '$email': $($result.Text)"
    }

    gcloud iam service-accounts create $Name --display-name $DisplayName --project $ProjectId
    return $email
}

$runtimeServiceAccountEmail = "$RuntimeServiceAccountName@$ProjectId.iam.gserviceaccount.com"
$deployerServiceAccountEmail = "$DeployerServiceAccountName@$ProjectId.iam.gserviceaccount.com"
$providerResource = "projects/$ProjectNumber/locations/global/workloadIdentityPools/$PoolId/providers/$ProviderId"

Invoke-Step -Message "Setting active gcloud project" -Action {
    gcloud config set project $ProjectId
}

Invoke-Step -Message "Enabling required APIs" -Action {
    gcloud services enable `
        run.googleapis.com `
        artifactregistry.googleapis.com `
        secretmanager.googleapis.com `
        iam.googleapis.com `
        iamcredentials.googleapis.com `
        --project $ProjectId
}

Invoke-Step -Message "Ensuring frontend runtime service account exists" -Action {
    $null = Ensure-ServiceAccount -Name $RuntimeServiceAccountName -DisplayName "GanttBuddy Frontend Runtime"
}

Invoke-Step -Message "Ensuring frontend deployer service account exists" -Action {
    $null = Ensure-ServiceAccount -Name $DeployerServiceAccountName -DisplayName "GitHub Actions Frontend Deployer"
}

Invoke-Step -Message "Granting deployer project roles" -Action {
    gcloud projects add-iam-policy-binding $ProjectId `
        --member "serviceAccount:$deployerServiceAccountEmail" `
        --role "roles/run.admin"

    gcloud projects add-iam-policy-binding $ProjectId `
        --member "serviceAccount:$deployerServiceAccountEmail" `
        --role "roles/artifactregistry.writer"

    gcloud projects add-iam-policy-binding $ProjectId `
        --member "serviceAccount:$deployerServiceAccountEmail" `
        --role "roles/logging.viewer"
}

Invoke-Step -Message "Allowing deployer to act as runtime service account" -Action {
    gcloud iam service-accounts add-iam-policy-binding $runtimeServiceAccountEmail `
        --member "serviceAccount:$deployerServiceAccountEmail" `
        --role "roles/iam.serviceAccountUser" `
        --project $ProjectId
}

Invoke-Step -Message "Ensuring GitHub workload identity provider exists" -Action {
    $result = Invoke-GcloudCapture -Arguments @(
        "iam", "workload-identity-pools", "providers", "describe", $ProviderId,
        "--location", "global",
        "--workload-identity-pool", $PoolId,
        "--project", $ProjectId
    )

    if ($result.ExitCode -eq 0) {
        Write-Host "Workload identity provider '$ProviderId' already exists."
    } else {
        if ($result.Text -notmatch "NOT_FOUND") {
            throw "Failed checking workload identity provider '$ProviderId': $($result.Text)"
        }

        gcloud iam workload-identity-pools providers create-oidc $ProviderId `
            --location global `
            --workload-identity-pool $PoolId `
            --display-name "GanttBuddy Frontend GitHub" `
            --issuer-uri "https://token.actions.githubusercontent.com" `
            --attribute-mapping "google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref" `
            --attribute-condition "assertion.repository=='$GithubOwner/$GithubRepo'" `
            --project $ProjectId
    }
}

Invoke-Step -Message "Allowing GitHub repo to impersonate deployer service account" -Action {
    gcloud iam service-accounts add-iam-policy-binding $deployerServiceAccountEmail `
        --role "roles/iam.workloadIdentityUser" `
        --member "principalSet://iam.googleapis.com/projects/$ProjectNumber/locations/global/workloadIdentityPools/$PoolId/attribute.repository/$GithubOwner/$GithubRepo" `
        --project $ProjectId
}

Invoke-Step -Message "Ensuring frontend secret exists" -Action {
    Ensure-Secret -Name $SecretName
}

if ($SecretsTomlPath) {
    Invoke-Step -Message "Publishing Streamlit secret version from $SecretsTomlPath" -Action {
        gcloud secrets versions add $SecretName --data-file $SecretsTomlPath --project $ProjectId
    }
}

Invoke-Step -Message "Granting runtime service account access to frontend secret" -Action {
    gcloud secrets add-iam-policy-binding $SecretName `
        --member "serviceAccount:$runtimeServiceAccountEmail" `
        --role "roles/secretmanager.secretAccessor" `
        --project $ProjectId
}

if ($CreateGithubVariables) {
    Invoke-Step -Message "Creating GitHub Actions variables" -Action {
        gh variable set "${GithubEnvironmentPrefix}_GCP_PROJECT_ID" --body $ProjectId
        gh variable set "${GithubEnvironmentPrefix}_GCP_REGION" --body $Region
        gh variable set "${GithubEnvironmentPrefix}_ARTIFACT_REGISTRY_REPOSITORY" --body $ArtifactRegistryRepository
        gh variable set "CLOUD_RUN_${GithubEnvironmentPrefix}_FRONTEND_SERVICE" --body $ServiceName
        gh variable set "CLOUD_RUN_${GithubEnvironmentPrefix}_FRONTEND_SERVICE_ACCOUNT" --body $runtimeServiceAccountEmail
        gh variable set "${GithubEnvironmentPrefix}_GCP_WORKLOAD_IDENTITY_PROVIDER" --body $providerResource
        gh variable set "${GithubEnvironmentPrefix}_GCP_WORKLOAD_IDENTITY_SERVICE_ACCOUNT" --body $deployerServiceAccountEmail
    }
}

if ($CreateGithubSecrets) {
    $envVarFile = Join-Path $PWD.Path "$($GithubEnvironmentPrefix.ToLowerInvariant())-frontend-env-vars.yaml"
    $secretMapFile = Join-Path $PWD.Path "$($GithubEnvironmentPrefix.ToLowerInvariant())-frontend-secrets.txt"

    Invoke-Step -Message "Creating helper files for GitHub secret upload" -Action {
        Set-Content -Path $envVarFile -Value "GANTTBUDDY_ENV: `"$($GithubEnvironmentPrefix.ToLowerInvariant())`"" -NoNewline
        Set-Content -Path $secretMapFile -Value "STREAMLIT_SECRETS_TOML=$SecretName`:latest" -NoNewline
        Write-Host "Created $envVarFile"
        Write-Host "Created $secretMapFile"
    }

    Invoke-Step -Message "Creating GitHub Actions secrets" -Action {
        Get-Content $envVarFile -Raw | gh secret set "CLOUD_RUN_${GithubEnvironmentPrefix}_FRONTEND_ENV_VARS"
        Get-Content $secretMapFile -Raw | gh secret set "CLOUD_RUN_${GithubEnvironmentPrefix}_FRONTEND_SECRETS"
    }
}

Write-Host ""
Write-Host "Bootstrap completed."
Write-Host "Project: $ProjectId"
Write-Host "Service: $ServiceName"
Write-Host "Runtime SA: $runtimeServiceAccountEmail"
Write-Host "Deployer SA: $deployerServiceAccountEmail"
Write-Host "Secret: $SecretName"
Write-Host "Provider: $providerResource"
Write-Host ""
Write-Host "Manual follow-up still required:"
Write-Host "1. Create/update the Google OAuth web client in this GCP project."
Write-Host "2. Set the exact redirect URI: https://<cloud-run-url>/oauth2callback"
Write-Host "3. Redeploy the frontend after uploading the real Streamlit secret."
Write-Host "4. Make the Cloud Run service browser-accessible with:"
Write-Host "   gcloud run services update $ServiceName --region=$Region --project=$ProjectId --no-invoker-iam-check"
Write-Host "5. Align the backend OIDC_CLIENT_ID with the frontend Google OAuth client ID."
