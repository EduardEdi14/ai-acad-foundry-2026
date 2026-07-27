<#
.SYNOPSIS
  Run the complete agent loop from the shell: thread → message → run → answer.

.DESCRIPTION
  Shows what the SDK does for you. Four REST calls, no libraries — the clearest
  possible demonstration that "the platform runs the loop" is a concrete claim
  about HTTP, not marketing.

.EXAMPLE
  ./03-invoke-agent.ps1 -Question "Why was my card blocked?"
  ./03-invoke-agent.ps1 -AgentId asst_abc123 -Question "..."
#>
param(
    [string]$Question   = "In one sentence: what do you do?",
    [string]$AgentId    = "",
    [string]$Persona    = "default",
    [string]$Name       = "libra-ai-acad-resource",
    [string]$Project    = "proj-default",
    [string]$ApiVersion = "2025-05-01"
)

$ErrorActionPreference = "Stop"
$projectUrl = "https://$Name.services.ai.azure.com/api/projects/$Project"
$res = "https://ai.azure.com"

function Rest($method, $path, $bodyObject = $null) {
    $url = "$projectUrl/$path" + $(if ($path -match '\?') { "&" } else { "?" }) + "api-version=$ApiVersion"
    if ($null -eq $bodyObject) {
        return az rest --method $method --url $url --resource $res -o json | ConvertFrom-Json
    }
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) "agent-req-$([guid]::NewGuid()).json"
    ($bodyObject | ConvertTo-Json -Depth 6) | Set-Content $tmp -Encoding UTF8
    try {
        return az rest --method $method --url $url --resource $res `
               --headers "Content-Type=application/json" --body "@$tmp" -o json | ConvertFrom-Json
    } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
}

# --- resolve the agent --------------------------------------------------------
if (-not $AgentId) {
    $list = Rest get "assistants"
    $match = $list.data | Where-Object { $_.name -eq $Persona } | Select-Object -First 1
    if (-not $match) {
        Write-Host "No hosted agent named '$Persona'. Create one first:" -ForegroundColor Red
        Write-Host "  ./02-create-agent.ps1 -Persona $Persona"
        exit 2
    }
    $AgentId = $match.id
}
Write-Host "agent    : $AgentId" -ForegroundColor Cyan
Write-Host "question : $Question`n"

# --- 1 · a thread is a conversation -------------------------------------------
Write-Host "[1] POST /threads              — open a conversation"
$thread = Rest post "threads" @{}
Write-Host "    thread id: $($thread.id)"

# --- 2 · add the user's message ------------------------------------------------
Write-Host "[2] POST /threads/{id}/messages — add the question"
Rest post "threads/$($thread.id)/messages" @{ role = "user"; content = $Question } | Out-Null

# --- 3 · start a run and poll --------------------------------------------------
Write-Host "[3] POST /threads/{id}/runs     — ask the platform to execute"
$run = Rest post "threads/$($thread.id)/runs" @{ assistant_id = $AgentId }
$deadline = (Get-Date).AddMinutes(2)
while ($run.status -in @("queued", "in_progress", "requires_action") -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 800
    $run = Rest get "threads/$($thread.id)/runs/$($run.id)"
    Write-Host "    status: $($run.status)"
}

if ($run.status -ne "completed") {
    Write-Host "`nRun ended as '$($run.status)'" -ForegroundColor Red
    if ($run.last_error) { Write-Host "  $($run.last_error | ConvertTo-Json -Compress)" }
    exit 3
}

# --- 4 · read the answer -------------------------------------------------------
Write-Host "[4] GET  /threads/{id}/messages — read what the agent wrote`n"
$messages = Rest get "threads/$($thread.id)/messages"
$answer = ($messages.data | Where-Object { $_.role -eq "assistant" } | Select-Object -First 1).content[0].text.value

Write-Host "─────────────────────────────────────────────────────────────"
Write-Host $answer
Write-Host "─────────────────────────────────────────────────────────────"
if ($run.usage) { Write-Host "tokens: $($run.usage.prompt_tokens) / $($run.usage.completion_tokens)" }
Write-Host "`nFour HTTP calls. That is the entire Agent Service protocol."
