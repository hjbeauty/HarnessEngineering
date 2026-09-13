# Windows PowerShell 5.1/7. Python runs only in the provided Docker image.
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][ValidateSet('prepare','check','conflict','resolve','restore')][string]$Action,
 [ValidateSet('start','review','conflict','final')][string]$Stage='start'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
foreach ($name in @('compose.yaml','.env','lesson03.ps1','course-tools/lesson05_context.py','starter/lesson05/CONTEXT_INDEX.md','templates/context_review.md','inputs/lesson03/sales.csv','records/lesson03/SHA256.json')) {
 if (-not (Test-Path -LiteralPath $name -PathType Leaf)) { throw "Required file missing: $name" }
}
if (Test-Path -LiteralPath '.\records\lesson05-pending.json') {
 throw 'An operation was interrupted. Preserve records\lesson05-pending.json and all backups; do not repeat actions.'
}
if ($Action -in @('prepare','restore')) {
 & .\lesson03.ps1 verify
 if (-not $?) { throw 'Baseline integrity check failed. Stop here.' }
 & docker compose stop hermes
 if ($LASTEXITCODE -ne 0) { throw 'Could not stop Hermes. No lesson files were changed.' }
}
# Only this short-lived Python helper receives the course folder. It does not start
# an Agent or a Dashboard. Normal Dashboard mounts remain as defined in compose.yaml.
& docker compose run --rm --no-deps -T --user hermes --workdir /tmp --entrypoint python --volume "${PSScriptRoot}:/course-host" hermes /course-tools/lesson05_context.py $Action $Stage
if ($LASTEXITCODE -ne 0) { throw "Lesson05 $Action stopped. Preserve the output and follow the recovery instructions." }
if ($Action -in @('prepare','restore')) {
 & .\lesson03.ps1 verify
 if (-not $?) { throw 'Baseline verification failed after the operation. Preserve the records.' }
}
if ($Action -eq 'prepare') {
 & docker compose up -d --force-recreate hermes
 if ($LASTEXITCODE -ne 0) { throw 'Preparation succeeded, but startup failed. Check Docker logs; do not repeat prepare.' }
 Write-Host 'Next: check healthy, open a new Hermes Chat, then .\lesson05.ps1 check start'
}
if ($Action -eq 'restore') {
 Write-Host 'Hermes is stopped. Next: docker compose up -d --force-recreate hermes'
 Write-Host 'Then check healthy, open a NEW Chat, and run .\lesson05.ps1 check start. Do not repeat prepare.'
}
