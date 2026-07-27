<#
.SYNOPSIS
  Delete the whole environment — the one-command cleanup.

.DESCRIPTION
  Deleting a resource group deletes everything inside it. That is the reason to put
  a course, an experiment or an environment in its own group: cleanup is one line,
  and nothing is left behind quietly costing money.

  Cognitive Services resources are soft-deleted by default; -Purge removes them
  completely so the name becomes available again immediately.

.EXAMPLE
  ./05-teardown.ps1
  ./05-teardown.ps1 -Purge -Force
#>
param(
    [string]$ResourceGroup = "libra-ai-acad",
    [string]$Name          = "libra-ai-acad-resource",
    [string]$Location      = "swedencentral",
    [switch]$Purge,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "`nAbout to DELETE resource group '$ResourceGroup' and everything in it:" -ForegroundColor Yellow
az resource list --resource-group $ResourceGroup --query "[].{name:name, type:type}" -o table

if (-not $Force) {
    $answer = Read-Host "`nType the resource group name to confirm"
    if ($answer -ne $ResourceGroup) { Write-Host "Cancelled."; exit 1 }
}

az group delete --name $ResourceGroup --yes --no-wait
Write-Host "Deletion started (running in the background)." -ForegroundColor Green

if ($Purge) {
    Write-Host "Purging the soft-deleted Cognitive Services account so the name is reusable..."
    $sub = az account show --query id -o tsv
    az rest --method delete --url ("https://management.azure.com/subscriptions/$sub" +
        "/providers/Microsoft.CognitiveServices/locations/$Location/resourceGroups/$ResourceGroup" +
        "/deletedAccounts/$Name" + "?api-version=2023-05-01") -o none 2>$null
    if ($?) { Write-Host "Purged." -ForegroundColor Green }
    else { Write-Host "Purge skipped (the group may still be deleting — retry in a few minutes)." -ForegroundColor Yellow }
}

Write-Host "`nCheck with:  az group exists --name $ResourceGroup`n"
