# Uses the already installed Docker runtime; does not require Windows Python.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('prepare','configure','before','freeze','verify')][string]$Action)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path '.\compose.yaml')) { throw 'Extract lesson 3 into the lesson 2 harness-engineering folder.' }
$recordsPath = Join-Path $PSScriptRoot 'records\lesson03'
New-Item -ItemType Directory -Force -Path $recordsPath | Out-Null
# Recording is done by a short-lived Python-only container, not an agent session.
# This is the only container given the records mount. Normal Hermes cannot see it.
if ($Action -eq 'freeze') {
    & docker compose stop hermes
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop Hermes. Baseline was not frozen.' }
}
& docker compose run --rm --no-deps -T --user hermes --entrypoint python --volume "${recordsPath}:/records" hermes /course-tools/lesson03_baseline.py $Action
if ($LASTEXITCODE -ne 0) { throw "Lesson 3 action failed: $Action. Preserve the error and follow the guide." }
