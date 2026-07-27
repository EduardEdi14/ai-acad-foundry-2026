<#
.SYNOPSIS
  Everything you own, in one screen: resource, deployments, quota, agents, roles.

.EXAMPLE
  ./04-inspect.ps1
#>
param(
    [string]$ResourceGroup = "libra-ai-acad",
    [string]$Name          = "libra-ai-acad-resource",
    [string]$Project       = "proj-default",
    [string]$Location      = "swedencentral",
    [string]$ApiVersion    = "2025-05-01"
)

$ErrorActionPreference = "Continue"
function Head($t) { Write-Host "`n$t" -ForegroundColor Cyan; Write-Host ("-" * 78) }

Head "SUBSCRIPTION"
az account show --query "{user:user.name, subscription:name, id:id, tenant:tenantId}" -o yaml

Head "FOUNDRY RESOURCE"
az cognitiveservices account show --name $Name --resource-group $ResourceGroup `
   --query "{name:name, kind:kind, sku:sku.name, location:location, endpoint:properties.endpoint}" -o yaml

Head "MODEL DEPLOYMENTS"
az cognitiveservices account deployment list --name $Name --resource-group $ResourceGroup `
   --query "[].{deployment:name, model:properties.model.name, version:properties.model.version, sku:sku.name, tpm:sku.capacity, state:properties.provisioningState}" -o table

Head "QUOTA IN USE ($Location)"
$usages = az cognitiveservices usage list --location $Location -o json | ConvertFrom-Json
$usages | Where-Object { $_.currentValue -gt 0 } |
    Select-Object @{n='quota';e={$_.name.value}}, @{n='used';e={[int]$_.currentValue}}, @{n='limit';e={[int]$_.limit}} |
    Format-Table -AutoSize

Head "HOSTED AGENTS"
$projectUrl = "https://$Name.services.ai.azure.com/api/projects/$Project"
$agents = az rest --method get --url "$projectUrl/assistants?api-version=$ApiVersion" `
          --resource "https://ai.azure.com" -o json 2>$null | ConvertFrom-Json
if ($agents.data) {
    $agents.data | Select-Object id, name, model, @{n='created';e={
        [DateTimeOffset]::FromUnixTimeSeconds($_.created_at).LocalDateTime.ToString('yyyy-MM-dd HH:mm')}} |
        Format-Table -AutoSize
} else {
    Write-Host "  (none — create one with ./02-create-agent.ps1)"
}

Head "YOUR ROLE ASSIGNMENTS ON THIS RESOURCE"
$res = az cognitiveservices account show --name $Name --resource-group $ResourceGroup --query id -o tsv
$me  = az ad signed-in-user show --query id -o tsv
az role assignment list --assignee $me --scope $res --query "[].{role:roleDefinitionName, scope:scope}" -o table

Write-Host "`nEverything above came from an API. None of it required the portal.`n" -ForegroundColor Green
