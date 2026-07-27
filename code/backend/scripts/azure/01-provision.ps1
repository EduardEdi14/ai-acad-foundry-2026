<#
.SYNOPSIS
  Build a complete Foundry environment from nothing — resource group, AI Services
  resource, model deployments and your own data-plane role assignment.

.DESCRIPTION
  Idempotent: every step checks before it creates, so re-running is safe.
  This is the script that replaces roughly twenty portal clicks.

.EXAMPLE
  ./01-provision.ps1
  ./01-provision.ps1 -ResourceGroup rg-ai-course -Name my-foundry-ana -Location swedencentral
#>
param(
    [string]$ResourceGroup = "libra-ai-acad",
    [string]$Name          = "libra-ai-acad-resource",
    [string]$Location      = "swedencentral",
    [string]$EmbeddingModel = "text-embedding-3-small",
    [int]   $Capacity      = 50
)

$ErrorActionPreference = "Stop"
function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }

# --- 0 · who are we, and where ------------------------------------------------
Step 0 "Signed-in identity and subscription"
$account = az account show -o json | ConvertFrom-Json
Write-Host "    user         : $($account.user.name)"
Write-Host "    subscription : $($account.name)  ($($account.id))"

# --- 1 · resource group -------------------------------------------------------
Step 1 "Resource group '$ResourceGroup' in $Location"
if ((az group exists --name $ResourceGroup) -eq "true") {
    Write-Host "    already exists — leaving it alone"
} else {
    az group create --name $ResourceGroup --location $Location -o none
    Write-Host "    created"
}

# --- 2 · the Foundry (AI Services) resource -----------------------------------
Step 2 "Foundry resource '$Name'"
$exists = az cognitiveservices account show --name $Name --resource-group $ResourceGroup -o json 2>$null
if ($exists) {
    Write-Host "    already exists"
} else {
    az cognitiveservices account create `
        --name $Name --resource-group $ResourceGroup --location $Location `
        --kind AIServices --sku S0 --yes -o none
    Write-Host "    created"
}
$endpoint = az cognitiveservices account show --name $Name --resource-group $ResourceGroup `
            --query properties.endpoint -o tsv
Write-Host "    endpoint : $endpoint"

# --- 3 · pick a chat model we actually have quota for -------------------------
Step 3 "Choosing a chat model with available quota in $Location"
$preferred = @("gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini", "gpt-5-nano", "gpt-4o")
$usages = az cognitiveservices usage list --location $Location -o json | ConvertFrom-Json

function Get-Available($model) {
    $u = $usages | Where-Object { $_.name.value -eq "OpenAI.GlobalStandard.$model" }
    if (-not $u) { return 0 }
    return [int]($u.limit - $u.currentValue)
}

$chatModel = $null
foreach ($m in $preferred) {
    $free = Get-Available $m
    Write-Host ("    {0,-16} free quota: {1}" -f $m, $free)
    if (-not $chatModel -and $free -ge $Capacity) { $chatModel = $m }
}
if (-not $chatModel) {
    Write-Host "`n    No preferred chat model has $Capacity K TPM free in $Location." -ForegroundColor Yellow
    Write-Host "    Quota is per subscription, per region, per model. Options: lower -Capacity," -ForegroundColor Yellow
    Write-Host "    choose another -Location, or request quota in the portal." -ForegroundColor Yellow
    exit 1
}
Write-Host "    → using $chatModel" -ForegroundColor Green

# --- 4 · deployments ----------------------------------------------------------
Step 4 "Model deployments"
$existing = az cognitiveservices account deployment list --name $Name --resource-group $ResourceGroup `
            -o json | ConvertFrom-Json

foreach ($model in @($chatModel, $EmbeddingModel)) {
    if ($existing.name -contains $model) {
        Write-Host "    $model — already deployed"
        continue
    }
    $version = az cognitiveservices model list --location $Location `
        --query "[?kind=='AIServices' && model.name=='$model'] | [-1].model.version" -o tsv
    az cognitiveservices account deployment create `
        --name $Name --resource-group $ResourceGroup `
        --deployment-name $model --model-name $model --model-version $version `
        --model-format OpenAI --sku-name GlobalStandard --sku-capacity $Capacity -o none
    Write-Host "    $model ($version) — deployed" -ForegroundColor Green
}

# --- 5 · the data-plane role (the step everyone forgets) ----------------------
Step 5 "Granting yourself the data-plane role"
$me  = az ad signed-in-user show --query id -o tsv
$res = az cognitiveservices account show --name $Name --resource-group $ResourceGroup --query id -o tsv
foreach ($role in @("Cognitive Services User", "Azure AI User")) {
    $have = az role assignment list --assignee $me --scope $res --role $role -o json | ConvertFrom-Json
    if ($have.Count -gt 0) {
        Write-Host "    '$role' — already assigned"
    } else {
        az role assignment create --assignee $me --scope $res --role $role -o none 2>$null
        if ($?) { Write-Host "    '$role' — assigned" -ForegroundColor Green }
        else    { Write-Host "    '$role' — could not assign (may need an administrator)" -ForegroundColor Yellow }
    }
}

# --- 6 · what to put in .env --------------------------------------------------
$base = $endpoint.TrimEnd('/') -replace '\.cognitiveservices\.azure\.com$', '.services.ai.azure.com'
Write-Host "`n─── put this in code/backend/.env ───────────────────────────────" -ForegroundColor Cyan
@"
LLM_PROVIDER=azure
EMBEDDING_PROVIDER=azure
AZURE_AI_ENDPOINT=https://$Name.services.ai.azure.com/models
AZURE_AI_AUTH=identity
AZURE_AI_CHAT_DEPLOYMENT=$chatModel
AZURE_AI_EMBEDDING_DEPLOYMENT=$EmbeddingModel
AZURE_AI_PROJECT_ENDPOINT=https://$Name.services.ai.azure.com/api/projects/proj-default
AZURE_RESOURCE_GROUP=$ResourceGroup
AZURE_FOUNDRY_RESOURCE=$Name
AZURE_LOCATION=$Location
"@ | Write-Host
Write-Host "─────────────────────────────────────────────────────────────────`n" -ForegroundColor Cyan
Write-Host "Verify with:  uv run python examples/02_hello_foundry.py" -ForegroundColor Green
