# Safely copy an extracted GO CFD source tree into the existing GitHub repository.
# Requires Git, an authenticated Git credential manager and write permission.
$ErrorActionPreference = 'Stop'
$repo = 'https://github.com/buildsmart888/go-cfd-ingetrazo.git'
$source = (Resolve-Path $PSScriptRoot).Path
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows first.' }
$work = Join-Path $env:TEMP ('go-cfd-sync-' + [guid]::NewGuid().ToString('N'))
& git clone $repo $work
if ($LASTEXITCODE -ne 0) { throw 'Could not clone existing repository. Sign into GitHub first.' }
try {
  Get-ChildItem -LiteralPath $source -Force | Where-Object {
    $_.Name -notin @('.git','.venv','venv','__pycache__','.pytest_cache','local_cases','dist','build')
  } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $work -Recurse -Force
  }
  Push-Location $work
  try {
    & git status --short
    & git add -A
    if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }
    & git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { Write-Host 'No changes to publish.'; return }
    & git commit -m 'feat: sync GO CFD extension source'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed: configure git user.name and user.email.' }
    & git push origin HEAD:main
    if ($LASTEXITCODE -ne 0) { throw 'Push failed. Remote may have advanced; re-clone and review.' }
  } finally { Pop-Location }
} finally {
  Write-Host "Review directory retained: $work"
}
