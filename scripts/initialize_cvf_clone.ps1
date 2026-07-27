param([string]$ProjectPath = "")

$ErrorActionPreference = "Stop"

function Resolve-FromProject([string]$Root, [string]$RelativePath) {
    return [System.IO.Path]::GetFullPath((Join-Path $Root $RelativePath))
}

if ([string]::IsNullOrWhiteSpace($ProjectPath)) { $ProjectPath = Split-Path -Parent $PSScriptRoot }
$projectResolved = [System.IO.Path]::GetFullPath($ProjectPath)
$manifestPath = Join-Path $projectResolved ".cvf\manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Portable CVF manifest not found: $manifestPath" }

$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json
$required = @("cvfCoreRepository", "cvfCoreCommit", "cvfCoreRelativePath", "workspaceRulesRelativePath")
$missing = @($required | Where-Object { -not ($manifest.PSObject.Properties.Name -contains $_) })
if ($missing.Count -gt 0) { throw "Manifest is not portable schema v2; missing: $($missing -join ', ')" }

$corePath = Resolve-FromProject $projectResolved $manifest.cvfCoreRelativePath
$workspaceRulesPath = Resolve-FromProject $projectResolved $manifest.workspaceRulesRelativePath
$workspaceRoot = Split-Path -Parent $workspaceRulesPath
if (-not (Test-Path -LiteralPath $corePath -PathType Container)) {
    New-Item -ItemType Directory -Path $workspaceRoot -Force | Out-Null
    git -c core.longpaths=true clone $manifest.cvfCoreRepository $corePath
    if ($LASTEXITCODE -ne 0) { throw "CVF core clone failed" }
}

git -C $corePath config core.longpaths true
if ($LASTEXITCODE -ne 0) { throw "Unable to enable long-path support in the CVF core clone" }

$pending = (git -C $corePath status --porcelain | Out-String).Trim()
if (-not [string]::IsNullOrWhiteSpace($pending)) { throw "Hidden CVF core is dirty; reconcile it before initialization: $corePath" }
git -C $corePath fetch origin main --quiet
if ($LASTEXITCODE -ne 0) { throw "Unable to fetch public CVF origin/main" }

$pin = [string]$manifest.cvfCoreCommit
git -C $corePath cat-file -e "$pin`^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) { throw "Pinned CVF commit is not available from the public repository: $pin" }
git -C $corePath merge-base --is-ancestor $pin origin/main 2>$null
if ($LASTEXITCODE -ne 0) { throw "Pinned CVF commit is not reachable from public origin/main: $pin" }

$head = (git -C $corePath rev-parse HEAD | Out-String).Trim()
if (-not $head.StartsWith($pin, [System.StringComparison]::OrdinalIgnoreCase)) {
    git -C $corePath merge-base --is-ancestor $head $pin 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Hidden core cannot fast-forward safely to pinned commit. Local=$head Pin=$pin" }
    git -C $corePath checkout main --quiet
    git -C $corePath merge --ff-only $pin
    if ($LASTEXITCODE -ne 0) { throw "Hidden core fast-forward failed" }
}

$binding = [ordered]@{
    schemaVersion = "1.0"; workspaceRoot = $workspaceRoot; workspaceRulesPath = $workspaceRulesPath
    cvfCorePath = $corePath; projectPath = $projectResolved
    resolvedCoreCommit = (git -C $corePath rev-parse HEAD | Out-String).Trim()
}
$bindingPath = Join-Path $projectResolved ".cvf\local-binding.json"
$binding | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $bindingPath -Encoding utf8
if (-not (Test-Path -LiteralPath $workspaceRulesPath -PathType Leaf)) {
    Copy-Item -LiteralPath (Join-Path $corePath "docs\reference\CVF_WORKSPACE_RULES.md") -Destination $workspaceRulesPath
}

$doctor = Join-Path $corePath "scripts\check_cvf_workspace_agent_enforcement.ps1"
& powershell -ExecutionPolicy Bypass -File $doctor -ProjectPath $projectResolved
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "FRESH_CLONE_CONTINUITY_PASS" -ForegroundColor Green
Write-Host "Project: $projectResolved"
Write-Host "Core:    $corePath @ $pin"
Write-Host "Read AGENTS.md, then resolve the canonical session state and active handoff."
