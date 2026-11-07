# Publish the full pre-release source archive

The initial GitHub repository contains a staged host plugin and project documentation. The complete validated offline source package is in the ChatGPT conversation attachment:
`GO_CFD_IngeTrazo_Source_v0.1.0-dev.zip`.

To replace the staged files with the complete source safely from your Windows PC:

1. Install Git for Windows and sign into GitHub.
2. Extract `GO_CFD_IngeTrazo_Source_v0.1.0-dev.zip`. Find the extracted directory holding `go_cfd`, `tests`, and `pyproject.toml`.
3. Open PowerShell. Run:

```powershell
git clone https://github.com/buildsmart888/go-cfd-ingetrazo.git
$destination = (Resolve-Path ./go-cfd-ingetrazo).Path
$source = (Resolve-Path "C:\PATH\TO\EXTRACTED\go-cfd-ingetrazo").Path
Get-ChildItem -LiteralPath $source -Force | Where-Object { $_.Name -ne '.git' -and $_.Name -ne '.pytest_cache' } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Force -Recurse
}
Set-Location $destination
python -m pip install -e '.[test]'
python -m pytest -q
git add -A
git commit -m "feat: import full GO CFD v0.1.0-dev source baseline"
git push origin main
```

**Caution:** Replace `C:\PATH\TO\EXTRACTED\go-cfd-ingetrazo` with the actual extracted source path. Review `git status` / `git diff --stat` before committing; do not upload `local_cases`, large meshes, log files, credentials or `.venv`.

The source archive already contains the full numerical and solver modules; these have not been reproduced in full in the GitHub staged files yet.

## Engineering checks

17/17 offline Python tests were previously completed on the complete local archive. Host IngeTrazo v0.6.0 and live OpenFOAM were not tested.
