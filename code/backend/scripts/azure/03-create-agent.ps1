<#
.SYNOPSIS
  Create a hosted agent in Foundry Agent Service — from the shell, with no SDK.

.DESCRIPTION
  Reads a persona JSON from app/agents/personas/ and POSTs it to the Agent Service
  REST API using `az rest`, which signs the request with your `az login` token.
  This is the same operation as scripts/deploy_agent.py — one uses the SDK, this
  one shows the HTTP call underneath.

.EXAMPLE
  ./02-create-agent.ps1 -Persona lyrical
#>
param(
    [string]$Persona    = "default",
    [string]$Name       = "libra-ai-acad-resource",
    [string]$Project    = "proj-default",
    [string]$Model      = "gpt-5-mini",
    [string]$ApiVersion = "2025-05-01"
)

$ErrorActionPreference = "Stop"
$projectUrl = "https://$Name.services.ai.azure.com/api/projects/$Project"

# --- 1 · read the persona file (the same file the app uses) -------------------
$personaPath = Join-Path $PSScriptRoot "..\..\app\agents\personas\$Persona.json"
if (-not (Test-Path $personaPath)) {
    Write-Host "No persona '$Persona'. Available:" -ForegroundColor Red
    Get-ChildItem (Join-Path $PSScriptRoot "..\..\app\agents\personas") -Filter *.json |
        ForEach-Object { "  $($_.BaseName)" }
    exit 2
}
$p = Get-Content $personaPath -Raw | ConvertFrom-Json

# --- 2 · compose the instructions exactly as persona.py does ------------------
$instructions = $p.instructions
if ($p.style_rules) {
    $rules = ($p.style_rules | ForEach-Object { "- $_" }) -join "`n"
    $instructions += "`n`nStyle rules you must follow:`n$rules"
}
if ($p.require_citations) {
    $instructions += "`n`nYou are given CONTEXT passages retrieved from the bank's own documents. " +
                     "Base your answer on those passages. Cite the passages you use as [1], [2], … ."
}

Write-Host "`nAgent to create" -ForegroundColor Cyan
Write-Host "  persona : $Persona ($($p.display_name))"
Write-Host "  model   : $Model"
Write-Host "  project : $projectUrl`n"

# --- 3 · does it already exist? -----------------------------------------------
$list = az rest --method get --url "$projectUrl/assistants?api-version=$ApiVersion" `
        --resource "https://ai.azure.com" -o json | ConvertFrom-Json
$existing = $list.data | Where-Object { $_.name -eq $Persona } | Select-Object -First 1

$body = @{ model = $Model; name = $Persona; description = $p.description; instructions = $instructions } |
        ConvertTo-Json -Depth 5
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) "agent-$Persona.json"
$body | Set-Content $tmp -Encoding UTF8

if ($existing) {
    Write-Host "Updating existing agent $($existing.id) …" -ForegroundColor Yellow
    $result = az rest --method post --url "$projectUrl/assistants/$($existing.id)?api-version=$ApiVersion" `
              --resource "https://ai.azure.com" --headers "Content-Type=application/json" `
              --body "@$tmp" -o json | ConvertFrom-Json
} else {
    Write-Host "Creating agent …" -ForegroundColor Green
    $result = az rest --method post --url "$projectUrl/assistants?api-version=$ApiVersion" `
              --resource "https://ai.azure.com" --headers "Content-Type=application/json" `
              --body "@$tmp" -o json | ConvertFrom-Json
}
Remove-Item $tmp -Force

Write-Host "`n✓ agent id : $($result.id)" -ForegroundColor Green
Write-Host "  name     : $($result.name)"
Write-Host "  model    : $($result.model)"
Write-Host "`nNext:"
Write-Host "  .env  →  FOUNDRY_AGENT_ID=$($result.id)"
Write-Host "  .env  →  AGENT_MODE=foundry"
Write-Host ('  or    ->  ./03-invoke-agent.ps1 -AgentId {0} -Question "your question"' -f $result.id)
