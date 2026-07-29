<#
.SYNOPSIS
  Create an Azure AI Search service and wire it into .env — the managed
  alternative to the Qdrant container.

.DESCRIPTION
  Qdrant in Docker is perfect for learning: it starts in two seconds and costs
  nothing. It is also yours to run, back up, scale and secure. Azure AI Search is
  the opposite trade: a monthly bill, and someone else's problem.

  This script creates the service, reads its admin key, and prints the three .env
  lines. The index itself is created by the application (POST /tools/azure-search/sync),
  because the vector dimension has to match whatever embedding model you deployed.

  Idempotent: every step checks before it creates.

.EXAMPLE
  ./07-provision-search.ps1
  ./07-provision-search.ps1 -ResourceGroup rg-ai-course -Name srch-ana -Sku basic
#>
param(
    [string]$ResourceGroup = "libra-ai-acad",
    [string]$Name          = "srch-libra-acad",
    [string]$Location      = "swedencentral",
    [ValidateSet("free", "basic", "standard")]
    [string]$Sku           = "basic",
    [switch]$Keyless                       # Entra-only; no admin key in .env
)

$ErrorActionPreference = "Stop"
function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }

# --- 0 · who are we -----------------------------------------------------------
Step 0 "Signed-in identity and subscription"
$account = az account show -o json | ConvertFrom-Json
Write-Host "    user         : $($account.user.name)"
Write-Host "    subscription : $($account.name)  ($($account.id))"

# --- 1 · the resource group ---------------------------------------------------
Step 1 "Resource group '$ResourceGroup'"
if ((az group exists --name $ResourceGroup) -eq "true") {
    Write-Host "    exists" -ForegroundColor DarkGray
} else {
    az group create --name $ResourceGroup --location $Location -o none
    Write-Host "    created in $Location" -ForegroundColor Green
}

# --- 2 · the search service ---------------------------------------------------
# free  : 1 index,  50 MB, no SLA, one per subscription — enough for this course
# basic : 15 indexes, 2 GB, SLA, ~EUR 70/month
# The sku CANNOT be changed later; you delete and recreate.
Step 2 "Search service '$Name' (sku: $Sku)"
$existing = az search service show --name $Name --resource-group $ResourceGroup -o json 2>$null
if ($existing) {
    $svc = $existing | ConvertFrom-Json
    Write-Host "    exists — sku $($svc.sku.name), status $($svc.status)" -ForegroundColor DarkGray
} else {
    $authOptions = if ($Keyless) { @("--aad-auth-failure-mode", "http401WithBearerChallenge",
                                     "--auth-options", "aadOrApiKey") }
                   else          { @("--auth-options", "aadOrApiKey",
                                     "--aad-auth-failure-mode", "http403") }
    az search service create `
        --name $Name --resource-group $ResourceGroup `
        --sku $Sku --location $Location `
        --partition-count 1 --replica-count 1 `
        @authOptions -o none
    Write-Host "    created — this takes a minute or two" -ForegroundColor Green
}

$endpoint = "https://$Name.search.windows.net"

# --- 3 · authentication -------------------------------------------------------
# Two lanes, exactly like the Foundry resource:
#   admin key   simple, works everywhere including containers, but it is a secret
#               that grants full read/write on every index in the service
#   Entra       no secret to leak, per-user roles, works with `az login` and with a
#               managed identity in production — but not with a bare container
Step 3 "Authentication lane"
if ($Keyless) {
    $objectId = az ad signed-in-user show --query id -o tsv
    $scope    = az search service show --name $Name --resource-group $ResourceGroup --query id -o tsv
    foreach ($role in @("Search Service Contributor", "Search Index Data Contributor")) {
        $held = az role assignment list --assignee $objectId --scope $scope `
                   --query "[?roleDefinitionName=='$role'] | length(@)" -o tsv
        if ($held -eq "0") {
            az role assignment create --assignee $objectId --role $role --scope $scope -o none
            Write-Host "    granted  : $role" -ForegroundColor Green
        } else {
            Write-Host "    already  : $role" -ForegroundColor DarkGray
        }
    }
    $key = ""
    Write-Host "    key      : none — the app will use your Entra identity"
} else {
    $key = az search admin-key show --service-name $Name --resource-group $ResourceGroup `
              --query primaryKey -o tsv
    Write-Host "    admin key: $($key.Substring(0,6))… (read/write on every index)"
}

# --- 4 · what to put in .env --------------------------------------------------
Step 4 "Configuration"
Write-Host ""
Write-Host "  AZURE_SEARCH_ENDPOINT=$endpoint"
Write-Host "  AZURE_SEARCH_INDEX=libra-docs"
Write-Host "  AZURE_SEARCH_KEY=$key"
Write-Host ""

$envFile = Join-Path $PSScriptRoot "..\..\.env"
if (Test-Path $envFile) {
    $answer = Read-Host "Write these into $((Resolve-Path $envFile).Path)? [y/N]"
    if ($answer -eq "y") {
        $lines = Get-Content $envFile
        foreach ($pair in @(@("AZURE_SEARCH_ENDPOINT", $endpoint),
                            @("AZURE_SEARCH_INDEX",    "libra-docs"),
                            @("AZURE_SEARCH_KEY",      $key))) {
            $pattern = "^$($pair[0])="
            if ($lines -match $pattern) { $lines = $lines -replace "$pattern.*", "$($pair[0])=$($pair[1])" }
            else                        { $lines += "$($pair[0])=$($pair[1])" }
        }
        Set-Content -Path $envFile -Value $lines -Encoding utf8
        Write-Host "    written" -ForegroundColor Green
    }
}

# --- 5 · next -----------------------------------------------------------------
Step 5 "Next"
Write-Host @"
    The service is empty. The index is created by the app, because its vector
    field has to match the dimension of your embedding deployment:

      POST http://localhost:7799/tools/azure-search/sync
           { "text": "...", "strategy": "sentence", "source": "handbook" }

    then query it three ways and compare:

      POST /tools/azure-search/query  { "query": "...", "mode": "keyword" }
      POST /tools/azure-search/query  { "query": "...", "mode": "vector"  }
      POST /tools/azure-search/query  { "query": "...", "mode": "hybrid"  }

    Portal: https://portal.azure.com/#@/resource$(az search service show --name $Name --resource-group $ResourceGroup --query id -o tsv)
"@
