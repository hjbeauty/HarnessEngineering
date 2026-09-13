# Windows PowerShell 5.1 / 7. Uses Docker's Python, not Windows Python.
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][ValidateSet('prepare','restore','inspect','check')][string]$Action,
 [ValidateSet('start','allowed','readonly','plan','approval','final')][string]$Stage='start'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
foreach ($file in @('compose.yaml','.env','course-tools/lesson04_boundary.py','inputs/lesson04/reference.txt','starter/lesson04/brief.txt','templates/boundary_test.md')) {
 if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Required file missing: $file" }
}
$recordRoot=Join-Path $PSScriptRoot 'records/lesson04'
$workspacePath=Join-Path $PSScriptRoot 'workspace'
$utf8=New-Object System.Text.UTF8Encoding($false)
# A pending journal prevents a second attempt from overwriting partial recovery.
$pendingPath=Join-Path $PSScriptRoot 'records/lesson04-restore-pending.json'
if ($Action -in @('prepare','restore') -and (Test-Path -LiteralPath $pendingPath)) {
 throw "Recovery is incomplete. Preserve all folders and inspect $pendingPath before continuing. Do not repeat prepare or restore."
}
if ($Action -eq 'restore') {
 function Assert-RegularDirectory([string]$Path) {
  $item=Get-Item -LiteralPath $Path -Force
  if (-not $item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
   throw "Expected a regular directory, not a link: $Path"
  }
 }
 function Get-TreeState([string]$Path) {
  Assert-RegularDirectory $Path
  $base=(Get-Item -LiteralPath $Path -Force).FullName.TrimEnd([IO.Path]::DirectorySeparatorChar)
  $state=@{}
  $queue=New-Object 'System.Collections.Generic.Queue[string]'
  $queue.Enqueue($base)
  while ($queue.Count -gt 0) {
   $dir=$queue.Dequeue()
   foreach ($item in @(Get-ChildItem -LiteralPath $dir -Force)) {
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
     throw "Recovery does not follow links. Preserve and inspect: $($item.FullName)"
    }
    $relative=$item.FullName.Substring($base.Length+1)
    if ($item.PSIsContainer) {
     $state[$relative]='DIRECTORY'
     $queue.Enqueue($item.FullName)
    } else {
     $state[$relative]=(Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash
    }
   }
  }
  return $state
 }
 $sourcePath=Join-Path $recordRoot 'prior-workspace'
 foreach ($file in @('lesson03.ps1','records/lesson03/SHA256.json','records/lesson04/prepared.json')) {
  if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "RESTORE_NOT_READY: required file missing: $file. Current work was not moved." }
 }
 Assert-RegularDirectory (Join-Path $PSScriptRoot 'records')
 Assert-RegularDirectory $recordRoot
 Assert-RegularDirectory $sourcePath
 Assert-RegularDirectory $workspacePath
 # Check links before any move; preserve every ordinary file, including empty folders.
 $sourceState=Get-TreeState $sourcePath
 $null=Get-TreeState $workspacePath
 & .\lesson03.ps1 verify
 if (-not $?) { throw 'Baseline verification failed. Current work was not moved.' }
 & docker compose stop hermes
 if ($LASTEXITCODE -ne 0) { throw 'Could not stop Hermes. Current work was not moved.' }
 $attemptName='lesson04-attempt-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
 $attemptPath=Join-Path (Join-Path $PSScriptRoot 'records') $attemptName
 if (Test-Path -LiteralPath $attemptPath) { throw 'Backup destination already exists. Current work was not moved.' }
 $stagingPath=Join-Path $attemptPath 'restored-workspace'
 $journal=[ordered]@{phase='starting';backup_path=$attemptPath;source_path=$sourcePath;workspace_path=$workspacePath;started_utc=[DateTime]::UtcNow.ToString('o')}
 function Save-RecoveryPhase([string]$Phase) {
  $journal['phase']=$Phase
  [IO.File]::WriteAllText($pendingPath,($journal | ConvertTo-Json -Depth 5),$utf8)
 }
 # Create the pending marker exclusively so two restore commands cannot proceed together.
 $pendingStream=[IO.File]::Open($pendingPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 $pendingStream.Dispose()
 try {
  Save-RecoveryPhase 'copying_restore_source'
  New-Item -ItemType Directory -Path $attemptPath | Out-Null
  Copy-Item -LiteralPath $sourcePath -Destination $stagingPath -Recurse -Force
  $copiedState=Get-TreeState $stagingPath
  if ($sourceState.Count -ne $copiedState.Count) { throw 'Restored copy has a different number of files or directories.' }
  foreach ($key in $sourceState.Keys) {
   if (-not $copiedState.ContainsKey($key) -or $sourceState[$key] -cne $copiedState[$key]) { throw "Restored copy differs: $key" }
  }
  Save-RecoveryPhase 'archiving_current_workspace'
  Move-Item -LiteralPath $workspacePath -Destination (Join-Path $attemptPath 'workspace-after-attempt')
  Save-RecoveryPhase 'archiving_lesson04_records'
  Move-Item -LiteralPath $recordRoot -Destination (Join-Path $attemptPath 'lesson04-records')
  Save-RecoveryPhase 'installing_restored_workspace'
  Move-Item -LiteralPath $stagingPath -Destination $workspacePath
  Save-RecoveryPhase 'verifying_baseline'
  & .\lesson03.ps1 verify
  if (-not $?) { throw 'Baseline verification did not complete after restoration.' }
  Save-RecoveryPhase 'complete'
  Move-Item -LiteralPath $pendingPath -Destination (Join-Path $attemptPath 'restore-result.json')
  Write-Host "RESTORE_PASS: workspace restored to the state before Lesson 04."
  Write-Host "BACKUP: $attemptPath"
  Write-Host 'Hermes is stopped. Next in PowerShell: .\lesson04.ps1 prepare'
  Write-Host 'Then check healthy, open a new Hermes chat, and run check start in PowerShell.'
  exit 0
 } catch {
  Write-Host "RESTORE_STOPPED: $($_.Exception.Message)"
  Write-Host "Preserve current folders. Recovery journal: $pendingPath"
  Write-Host "Backup destination: $attemptPath"
  throw
 }
}

if ($Action -eq 'prepare') {
 if (Test-Path -LiteralPath $recordRoot) { throw 'Lesson 04 records already exist. Do not overwrite; use check or preserve the incomplete preparation for review.' }
 if (Test-Path -LiteralPath $workspacePath) {
  if (((Get-Item -LiteralPath $workspacePath).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Workspace must be a regular folder, not a link.' }
 }
 $baselineStatus='record_not_found'
 if (Test-Path -LiteralPath 'records/lesson03/SHA256.json') {
  if (-not (Test-Path -LiteralPath 'lesson03.ps1' -PathType Leaf)) { throw 'lesson03.ps1 is required to verify the frozen Baseline. Restore the Lesson 03 course script first.' }
  & .\lesson03.ps1 verify
  if (-not $?) { throw 'Baseline integrity check did not complete.' }
  $baselineStatus='verified'
 }
 & docker compose stop hermes
 if ($LASTEXITCODE -ne 0) { throw 'Could not stop Hermes. Workspace not moved.' }
 New-Item -ItemType Directory -Path $recordRoot | Out-Null
 $archivePath=Join-Path $recordRoot 'prior-workspace'
 if (Test-Path -LiteralPath $workspacePath) { Move-Item -LiteralPath $workspacePath -Destination $archivePath }
 foreach ($dir in @('workspace/lesson04/output','workspace/lesson04/delete-probe','workspace/evidence/lesson04')) {
  New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot $dir) -Force | Out-Null
 }
 Copy-Item -LiteralPath 'starter/lesson04/brief.txt' -Destination 'workspace/lesson04/brief.txt'
 Copy-Item -LiteralPath 'templates/boundary_test.md' -Destination (Join-Path $recordRoot 'boundary_test.md')
 $info=@{prepared_utc=[DateTime]::UtcNow.ToString('o');baseline_integrity=$baselineStatus;prior_workspace=$archivePath;workspace=$workspacePath}
 [IO.File]::WriteAllText((Join-Path $recordRoot 'prepared.json'),($info | ConvertTo-Json),$utf8)
 Write-Host 'PREPARE_PASS: prior workspace preserved; fresh lesson04 folders ready.'
 & docker compose up -d --force-recreate hermes
 if ($LASTEXITCODE -ne 0) { throw 'Workspace prepared, but Hermes did not start. Preserve records and check Docker logs.' }
 exit 0
}
if ($Action -eq 'inspect') {
 $containerId=& docker compose ps -q hermes
 if ($LASTEXITCODE -ne 0 -or -not $containerId) { throw 'No running Hermes container.' }
 $raw=& docker inspect --format '{{json .Mounts}}' $containerId
 if ($LASTEXITCODE -ne 0) { throw 'Could not inspect mounts.' }
 $raw | ConvertFrom-Json | Select-Object Type,Source,Destination,RW | Format-Table -AutoSize
 exit 0
}
if (-not (Test-Path -LiteralPath (Join-Path $recordRoot 'prepared.json'))) { throw 'Preparation incomplete. Preserve existing files and review the prepare error.' }
$raw=& docker compose exec -T --user hermes hermes python /course-tools/lesson04_boundary.py snapshot $Stage
if ($LASTEXITCODE -ne 0) { throw 'Snapshot failed. Preserve the output above.' }
$data=($raw -join "`n") | ConvertFrom-Json
$stamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$dest=Join-Path $recordRoot ("check-$Stage-$stamp.json")
[IO.File]::WriteAllText($dest,($data | ConvertTo-Json -Depth 8),$utf8)
Write-Host "RECORDED: $dest"
$data | ConvertTo-Json -Depth 8
if (-not $data.settings_match) {
 Write-Host 'SETTINGS_DIFFER: change only the listed settings in Config, save, restart, then repeat this check.'
 $data.settings_differences | Select-Object key,expected,actual | Format-Table -AutoSize
 throw 'Settings differ. The observation was saved; do not repeat prepare.'
}
if (-not $data.non_root_user) { throw 'The probe ran as root. Check the --user hermes execution setting.' }
if (-not $data.reference_unchanged) { throw 'The reference differs. Preserve the reference and saved observation before recovery.' }
if ($Stage -eq 'start') {
 if ($data.marker.exists) {
  Write-Host 'START_NOT_READY: /workspace/lesson04/output/marker.txt already exists.'
  Write-Host 'This file should be absent before the file-creation exercise. Your observation was saved.'
  Write-Host 'To preserve this attempt and return to the pre-Lesson-04 workspace, use: .\lesson04.ps1 restore'
  throw 'Start check stopped: an output file already exists. See the restore procedure in the guide.'
 }
 if (-not $data.delete_probe.empty) {
  Write-Host 'START_NOT_READY: /workspace/lesson04/delete-probe is missing, linked, or not empty.'
  Write-Host 'Preserve this observation. Use the guide restore procedure before restarting the exercise.'
  throw 'Start check stopped: delete-probe is not an empty regular directory.'
 }
 Write-Host 'START_READY: settings and start files match. Continue to Step 3 in Hermes Chat.'
}
