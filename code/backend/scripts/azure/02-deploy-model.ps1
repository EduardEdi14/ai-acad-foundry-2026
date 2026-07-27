<#
.SYNOPSIS
  Deploy an additional model into your existing Foundry resource — from the CLI only.

.DESCRIPTION
  A deployment is *your named instance* of a catalog model: model + version + serving
  type + a slice of quota. Your code then calls the DEPLOYMENT NAME, never "the model".
  That indirection is what lets an organization swap or throttle models without
  touching application code.

  Run with no arguments to see what the catalog offers in your region together with
  the quota you actually have — the two facts that decide what you can deploy.

.EXAMPLE
  ./02-deploy-model.ps1                                  # list what is available
  ./02-deploy-model.ps1 -Model gpt-4.1-mini              # deploy it
  ./02-deploy-model.ps1 -Model gpt-4.1-mini -DeploymentName fast -Capacity 20
  ./02-deploy-model.ps1 -Model gpt-4o -Delete            # remove a deployment
#>
param(
    [string]$Model          = "",
    [string]$DeploymentName = "",
    [string]$ResourceGroup  = "libra-ai-acad",
    [string]$Name           = "libra-ai-acad-resource",
    [string]$Location       = "swedencentral",
    [string]$Sku            = "GlobalStandard",
    [int]   $Capacity       = 50,
    [string]$Version        = "",
    [switch]$Delete
)

$ErrorActionPreference = "Stop"
function Head($t) { Write-Host "`n$t" -ForegroundColor Cyan; Write-Host ("-" * 74) }

# --- what is already deployed --------------------------------------------------
Head "CURRENT DEPLOYMENTS in $Name"
az cognitiveservices account deployment list --name $Name --resource-group $ResourceGroup `
   --query "[].{deployment:name, model:properties.model.name, version:properties.model.version, sku:sku.name, tpm:sku.capacity, state:properties.provisioningState}" -o table

# --- delete mode ---------------------------------------------------------------
if ($Delete) {
    if (-not $Model) { Write-Host "`nGive -Model (the deployment name) to delete." -ForegroundColor Red; exit 1 }
    $target = if ($DeploymentName) { $DeploymentName } else { $Model }
    Write-Host "`nDeleting deployment '$target' …" -ForegroundColor Yellow
    az cognitiveservices account deployment delete --name $Name --resource-group $ResourceGroup `
       --deployment-name $target -o none
    Write-Host "Deleted. Quota is released immediately." -ForegroundColor Green
    exit 0
}

# --- discovery mode: no model given -------------------------------------------
$usages = az cognitiveservices usage list --location $Location -o json | ConvertFrom-Json
function FreeQuota($m, $skuName) {
    $u = $usages | Where-Object { $_.name.value -eq "OpenAI.$skuName.$m" }
    if (-not $u) { return $null }
    return [int]($u.limit - $u.currentValue)
}

if (-not $Model) {
    Head "AVAILABLE IN $Location (chat + embeddings, with YOUR remaining quota)"
    $catalog = az cognitiveservices model list --location $Location -o json | ConvertFrom-Json
    $rows = @()
    foreach ($entry in ($catalog | Where-Object { $_.kind -eq 'AIServices' })) {
        $m = $entry.model.name
        if ($m -notmatch 'gpt|embedding|phi|mistral|llama|deepseek') { continue }
        if ($m -match 'audio|realtime|transcribe|image|sora|codex|dalle') { continue }
        $free = FreeQuota $m $Sku
        if ($null -eq $free -or $free -le 0) { continue }
        $rows += [pscustomobject]@{
            Model = $m; Version = $entry.model.version; FreeQuota = $free
            Skus  = ($entry.model.skus.name | Select-Object -Unique) -join ','
        }
    }
    $rows | Sort-Object Model -Unique | Format-Table -AutoSize

    Write-Host "Quota is per subscription, per region, per model — a model with 0 free quota"
    Write-Host "cannot be deployed here even though it appears in the catalog.`n"
    Write-Host "Deploy one with:" -ForegroundColor Green
    Write-Host "  ./02-deploy-model.ps1 -Model <name> [-DeploymentName <alias>] [-Capacity <K TPM>]"
    exit 0
}

# --- deploy --------------------------------------------------------------------
if (-not $DeploymentName) { $DeploymentName = $Model }

Head "DEPLOYING $Model  ->  deployment '$DeploymentName'"

$free = FreeQuota $Model $Sku
if ($null -ne $free -and $free -lt $Capacity) {
    Write-Host "Only ${free}K TPM free for $Model ($Sku) in $Location; you asked for ${Capacity}K." -ForegroundColor Yellow
    if ($free -le 0) {
        Write-Host "Nothing to deploy into. Pick another model, region, or request quota." -ForegroundColor Red
        exit 1
    }
    $Capacity = $free
    Write-Host "Reducing capacity to ${Capacity}K." -ForegroundColor Yellow
}

if (-not $Version) {
    $Version = az cognitiveservices model list --location $Location `
        --query "[?kind=='AIServices' && model.name=='$Model'] | [-1].model.version" -o tsv
    if (-not $Version) {
        Write-Host "Model '$Model' is not offered in $Location." -ForegroundColor Red
        Write-Host "Run without -Model to see what is." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "  model    : $Model"
Write-Host "  version  : $Version"
Write-Host "  sku      : $Sku"
Write-Host "  capacity : ${Capacity}K tokens/minute`n"

az cognitiveservices account deployment create `
    --name $Name --resource-group $ResourceGroup `
    --deployment-name $DeploymentName --model-name $Model --model-version $Version `
    --model-format OpenAI --sku-name $Sku --sku-capacity $Capacity -o none

Write-Host "Deployed." -ForegroundColor Green
az cognitiveservices account deployment show --name $Name --resource-group $ResourceGroup `
   --deployment-name $DeploymentName `
   --query "{deployment:name, model:properties.model.name, state:properties.provisioningState, tpm:sku.capacity}" -o yaml

Write-Host "`nUse it from code by NAME:" -ForegroundColor Cyan
Write-Host "  .env  ->  AZURE_AI_CHAT_DEPLOYMENT=$DeploymentName"
Write-Host "  or per call:  client.complete(model=`"$DeploymentName`", ...)"
Write-Host "`nIt is also visible now in ai.azure.com -> Models + endpoints.`n"
