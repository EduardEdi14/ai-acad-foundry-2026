<#
.SYNOPSIS
  Give the container an identity of its own, so the whole application can run in
  Docker with no `az login` and no API key.

.DESCRIPTION
  A container cannot read your `az login`: that token cache lives in your Windows
  user profile, and the container has its own filesystem. So a container on a
  laptop is anonymous, falls back to an API key, and loses everything that
  requires Microsoft Entra - the Foundry Agent Service and every control-plane
  call.

  A service principal fixes that. It is an application identity with its own
  client id and secret. DefaultAzureCredential tries EnvironmentCredential first,
  so putting three variables in .env is all it takes - no code changes anywhere.

  In Azure you would use a managed identity instead and have no secret at all
  (see docs/sessions/s06-shipping-containers.html). A service principal is the
  right answer for exactly one situation: a container running outside Azure.

  Idempotent: if the principal already exists its secret is reset, so re-running
  gives you a fresh credential rather than an error.

.EXAMPLE
  ./09-create-service-principal.ps1
  ./09-create-service-principal.ps1 -Name sp-my-console -ResourceGroup rg-ai-course
#>
param(
    [string]$Name          = "sp-libra-acad-container",
    [string]$ResourceGroup = "libra-ai-acad",
    [int]   $Years         = 1,
    [switch]$NoWrite                       # print the values, do not touch .env
)

$ErrorActionPreference = "Stop"
function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }

# --- 0 - who are we -----------------------------------------------------------
Step 0 "Signed-in identity"
$account = az account show -o json | ConvertFrom-Json
Write-Host "    user         : $($account.user.name)"
Write-Host "    subscription : $($account.name)"
Write-Host "    tenant       : $($account.tenantId)"

$scope = az group show --name $ResourceGroup --query id -o tsv
if (-not $scope) { throw "Resource group '$ResourceGroup' not found." }
Write-Host "    scope        : $ResourceGroup"

# --- 1 - the principal --------------------------------------------------------
# Scoped to the resource group, not the subscription. Everything this application
# touches lives in one group, so the identity has no reach beyond it. Widening a
# scope later is one command; explaining why a service account could read the
# whole subscription is a longer conversation.
Step 1 "Service principal '$Name'"
$existing = az ad sp list --display-name $Name --query "[0].appId" -o tsv

if ($existing) {
    Write-Host "    exists ($existing) - resetting its secret" -ForegroundColor DarkGray
    $sp = az ad sp credential reset --id $existing --years $Years -o json | ConvertFrom-Json
} else {
    $sp = az ad sp create-for-rbac --name $Name --years $Years `
             --role "Cognitive Services User" --scopes $scope -o json | ConvertFrom-Json
}

$appId    = $sp.appId
$password = $sp.password
$tenant   = $sp.tenant

# Creating a service principal is a DIRECTORY operation, not a subscription one. Owning
# a subscription does not imply the right to register an application in the tenant, and
# most managed tenants (universities, banks) switch that right off for ordinary users.
# Running the shell as administrator changes nothing - the permission is in Entra.
if (-not $appId) {
    Write-Host ""
    Write-Host "  Could not create the service principal." -ForegroundColor Red
    Write-Host @"

  If the error above says 'Insufficient privileges', this is a tenant policy, not a
  problem with this script and not something local administrator rights can fix.
  Ask whoever administers tenant $($account.tenantId) for ONE of:

    - the 'Application Developer' Entra role for $($account.user.name), or
    - Entra ID > Users > User settings > 'Users can register applications' = Yes, or
    - a service principal created for you, and its appId / secret / tenant

  Until then the container falls back to key authentication, which is enough for
  chat, embeddings, speech, Azure AI Search and every local agent. Only the hosted
  Foundry Agent Service and the Azure control-plane panel need Entra:

    DOCKER_AZURE_AI_AUTH=key      (the default in .env)

"@ -ForegroundColor Yellow
    exit 1
}
if (-not $existing) { Write-Host "    created ($appId)" -ForegroundColor Green }

# The object id is what role assignments use - it is NOT the same as the app id.
$objectId = az ad sp show --id $appId --query id -o tsv

# --- 2 - the roles it needs ---------------------------------------------------
# One role per capability, each scoped to the resource group. Read them as a list
# of what the container is allowed to do, because that is exactly what it is.
Step 2 "Role assignments"
$roles = @(
    @{ name = "Cognitive Services User";        why = "chat, embeddings, speech" },
    @{ name = "Azure AI User";                  why = "the Foundry Agent Service" },
    @{ name = "Search Index Data Contributor";  why = "Azure AI Search, keyless" }
)
foreach ($role in $roles) {
    $held = az role assignment list --assignee $objectId --scope $scope `
               --query "[?roleDefinitionName=='$($role.name)'] | length(@)" -o tsv
    if ($held -eq "0") {
        try {
            az role assignment create --assignee-object-id $objectId `
                --assignee-principal-type ServicePrincipal `
                --role $role.name --scope $scope -o none
            Write-Host "    granted  : $($role.name)  ($($role.why))" -ForegroundColor Green
        } catch {
            Write-Host "    SKIPPED  : $($role.name) - $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    already  : $($role.name)  ($($role.why))" -ForegroundColor DarkGray
    }
}

# --- 3 - write it into .env ---------------------------------------------------
Step 3 "Configuration"
$lines = @(
    "DOCKER_AZURE_AI_AUTH=identity",
    "AZURE_CLIENT_ID=$appId",
    "AZURE_CLIENT_SECRET=$password",
    "AZURE_TENANT_ID=$tenant"
)

if ($NoWrite) {
    Write-Host ""
    $lines | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
} else {
    $envFile = Join-Path $PSScriptRoot "..\..\.env"
    if (-not (Test-Path $envFile)) { throw "No .env at $envFile - copy .env.example first." }
    $content = Get-Content $envFile
    foreach ($line in $lines) {
        $key = $line.Split("=")[0]
        if ($content -match "^$key=") { $content = $content -replace "^$key=.*", $line }
        else                          { $content += $line }
    }
    Set-Content -Path $envFile -Value $content -Encoding utf8
    Write-Host "    written to $((Resolve-Path $envFile).Path)" -ForegroundColor Green
    Write-Host "    secret shown once by Azure and never again - it is only in .env now"
}

# --- 4 - next -----------------------------------------------------------------
Step 4 "Next"
Write-Host @"
    The whole stack can now run in Docker, keyless:

      cd code/backend
      docker compose up -d --build

    Then prove the container has a real identity - this is the call that was
    failing before, because a key cannot reach the Agent Service:

      irm http://localhost:7799/agents | ConvertTo-Json -Depth 4
      #  look for:  "foundry": { "available": true, "reason": null }

    Console: http://localhost:7800

    Role assignments take a few seconds to propagate. If the first call reports
    unavailable, wait a minute and repeat it before changing anything.
"@
