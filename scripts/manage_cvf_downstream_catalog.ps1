# Template copied verbatim by bootstrap to <project>/scripts/manage_cvf_downstream_catalog.ps1.
# Do not execute this core-side copy in place; its sibling-lib relative path
# only resolves correctly once installed at the downstream project root.
param(
    [switch]$Check,
    [switch]$Write,
    [string]$ProjectPath = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = Split-Path -Parent $PSScriptRoot
}
$projectResolved = [System.IO.Path]::GetFullPath($ProjectPath)
$libPath = Join-Path $PSScriptRoot "lib\downstream_catalog\CvfDownstreamCatalogLib.ps1"
. $libPath

if (-not $Check -and -not $Write) { $Check = $true }

$artifactRegistryPath = Join-Path $projectResolved "docs\catalog\ARTIFACT_REGISTRY.json"
$moduleRegistryPath = Join-Path $projectResolved "docs\catalog\MODULE_REGISTRY.json"
$indexPath = Join-Path $projectResolved "docs\INDEX.md"
$moduleCatalogPath = Join-Path $projectResolved "docs\catalog\MODULE_CATALOG.md"

$violations = [System.Collections.Generic.List[string]]::new()

foreach ($required in @($artifactRegistryPath, $moduleRegistryPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        Write-Host "[FAIL] required catalog source missing: $required" -ForegroundColor Red
        exit 1
    }
}

try { $artifactRegistry = Get-Content -LiteralPath $artifactRegistryPath -Raw -Encoding utf8 | ConvertFrom-Json }
catch { Write-Host "[FAIL] ARTIFACT_REGISTRY.json is not valid JSON: $_" -ForegroundColor Red; exit 1 }

try { $moduleRegistry = Get-Content -LiteralPath $moduleRegistryPath -Raw -Encoding utf8 | ConvertFrom-Json }
catch { Write-Host "[FAIL] MODULE_REGISTRY.json is not valid JSON: $_" -ForegroundColor Red; exit 1 }

$activeStatePath = Join-Path $projectResolved "CVF_SESSION\ACTIVE_SESSION_STATE.json"
$initialHandoffRelative = "CVF_SESSION/handoffs/AGENT_HANDOFF_V1_UNKNOWN.md"
if (Test-Path -LiteralPath $activeStatePath -PathType Leaf) {
    try {
        $activeState = Get-Content -LiteralPath $activeStatePath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($activeState.activeHandoff) { $initialHandoffRelative = [string]$activeState.activeHandoff }
    }
    catch { }
}

$violations.AddRange([string[]](Test-CvfArtifactRegistry -Registry $artifactRegistry -ProjectRoot $projectResolved))
$violations.AddRange([string[]](Test-CvfArtifactRegistryBaseline -Registry $artifactRegistry -InitialHandoffRelative $initialHandoffRelative))
$violations.AddRange([string[]](Test-CvfModuleRegistry -Registry $moduleRegistry -ProjectRoot $projectResolved))
$violations.AddRange([string[]](Test-CvfRegistryProjectIdentity -ArtifactRegistry $artifactRegistry -ModuleRegistry $moduleRegistry))

if ($violations.Count -gt 0) {
    Write-Host "[FAIL] Governed downstream catalog validation failed:" -ForegroundColor Red
    foreach ($v in $violations) { Write-Host "  - $v" -ForegroundColor Red }
    exit 1
}

$expectedIndex = ConvertTo-CvfIndexMarkdown -Registry $artifactRegistry
$expectedModuleCatalog = ConvertTo-CvfModuleCatalogMarkdown -Registry $moduleRegistry

if ($Write) {
    Set-Content -LiteralPath $indexPath -Value $expectedIndex -Encoding utf8 -NoNewline
    Set-Content -LiteralPath $moduleCatalogPath -Value $expectedModuleCatalog -Encoding utf8 -NoNewline
    Write-Host "[OK] Regenerated docs/INDEX.md and docs/catalog/MODULE_CATALOG.md from registries." -ForegroundColor Green
    exit 0
}

$driftViolations = [System.Collections.Generic.List[string]]::new()
if (-not (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
    $driftViolations.Add("docs/INDEX.md is missing")
}
elseif ((Get-Content -LiteralPath $indexPath -Raw -Encoding utf8) -ne $expectedIndex) {
    $driftViolations.Add("docs/INDEX.md does not match the generated view rendered from ARTIFACT_REGISTRY.json (hand-edited or stale)")
}
if (-not (Test-Path -LiteralPath $moduleCatalogPath -PathType Leaf)) {
    $driftViolations.Add("docs/catalog/MODULE_CATALOG.md is missing")
}
elseif ((Get-Content -LiteralPath $moduleCatalogPath -Raw -Encoding utf8) -ne $expectedModuleCatalog) {
    $driftViolations.Add("docs/catalog/MODULE_CATALOG.md does not match the generated view rendered from MODULE_REGISTRY.json (hand-edited or stale)")
}

if ($driftViolations.Count -gt 0) {
    Write-Host "[FAIL] Generated view drift detected:" -ForegroundColor Red
    foreach ($v in $driftViolations) { Write-Host "  - $v" -ForegroundColor Red }
    Write-Host "  Run with -Write to regenerate the views from source truth." -ForegroundColor Yellow
    exit 1
}

Write-Host "[PASS] Governed downstream catalog is valid and generated views match source truth." -ForegroundColor Green
exit 0
