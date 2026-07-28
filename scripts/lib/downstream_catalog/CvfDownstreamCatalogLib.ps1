# CVF Downstream Catalog Library
#
# Standard-library-only PowerShell functions shared by the bootstrap kit and
# by the generated project's own catalog manager. This file is copied
# verbatim into every bootstrapped downstream project at
# scripts/lib/downstream_catalog/CvfDownstreamCatalogLib.ps1 so the manager
# can run without depending on the CVF core at runtime.

$Script:CvfCatalogKitVersion = "1.1"

$Script:CvfArtifactFamilies = @(
    "schema", "tool", "manifest", "policy", "continuity",
    "implementation_truth", "generated_view", "governed_artifact_family"
)
$Script:CvfArtifactStatuses = @("ACTIVE", "DEPRECATED", "RETIRED")

# Source-backed only: no vocabulary token may represent roadmap/plan-only
# intent (BSL-R4). A module's status must be justified by its required
# `evidence` field, not by aspiration.
$Script:CvfModuleStatuses = @("ENFORCED", "PARTIAL", "CONTRACT_ONLY", "STUB", "DEPRECATED")
$Script:CvfControlPattern = "^GC-[0-9]{3}$"

$Script:CvfArtifactRegistryTopLevelFields = @("schemaVersion", "projectName", "updatedAt", "claimBoundary", "artifacts")
$Script:CvfArtifactEntryFields = @("id", "family", "path", "status", "description")

$Script:CvfModuleRegistryTopLevelFields = @("schemaVersion", "projectName", "updatedAt", "claimBoundary", "modules")
$Script:CvfModuleEntryRequiredFields = @("id", "name", "path", "status", "description", "evidence")
$Script:CvfModuleEntryOptionalFields = @("controls", "dependencies")
$Script:CvfModuleEntryAllowedFields = $Script:CvfModuleEntryRequiredFields + $Script:CvfModuleEntryOptionalFields

function Test-CvfObjectShape {
    # Enforces the closed-schema contract generically: every required field
    # must be present, and no field outside AllowedFields may be present
    # (JSON Schema additionalProperties: false). Used for both top-level
    # registry documents and individual entries.
    param(
        [Parameter(Mandatory = $true)]$Obj,
        [Parameter(Mandatory = $true)][string[]]$RequiredFields,
        [Parameter(Mandatory = $true)][string[]]$AllowedFields,
        [Parameter(Mandatory = $true)][string]$ContextLabel
    )
    $violations = [System.Collections.Generic.List[string]]::new()
    if ($null -eq $Obj -or $Obj -isnot [System.Management.Automation.PSCustomObject]) {
        $violations.Add("$ContextLabel`: expected a JSON object")
        return , $violations.ToArray()
    }
    $presentNames = @($Obj.PSObject.Properties.Name)
    foreach ($required in $RequiredFields) {
        if ($presentNames -notcontains $required) {
            $violations.Add("$ContextLabel`: missing required field '$required'")
        }
    }
    foreach ($name in $presentNames) {
        if ($AllowedFields -notcontains $name) {
            $violations.Add("$ContextLabel`: additional property not allowed '$name'")
        }
    }
    return , $violations.ToArray()
}

function Test-CvfStringField {
    # Mutates $Violations (a List[string], reference type) in place.
    param($Obj, [string]$FieldName, [string]$ContextLabel, $Violations, [bool]$Required = $true)
    if ($Obj.PSObject.Properties.Name -notcontains $FieldName) { return }
    $value = $Obj.$FieldName
    if ($null -eq $value) {
        if ($Required) { $Violations.Add("$ContextLabel`: field '$FieldName' must not be null") }
        return
    }
    if ($value -isnot [string]) {
        $Violations.Add("$ContextLabel`: field '$FieldName' must be a string")
        return
    }
    if ($Required -and [string]::IsNullOrWhiteSpace($value)) {
        $Violations.Add("$ContextLabel`: field '$FieldName' must be non-empty")
    }
}

function ConvertTo-CvfSafeCollection {
    # @($null) produces a ONE-element array containing $null (a well-known
    # PowerShell pitfall), not an empty array - unlike @($realEmptyArray),
    # which correctly stays empty. A field that is simply absent (e.g.
    # "artifacts" removed entirely) reads back as $null, so iterating
    # @($Registry.artifacts) directly would loop once over a null entry and
    # crash the first Mandatory-parameter call it hits. Always route
    # collection fields through this helper before iterating.
    param($Value)
    if ($null -eq $Value) { return , @() }
    return , @($Value)
}

function Test-CvfArrayField {
    # Optional array-typed field: absent/null is fine, present-but-wrong-type
    # is not.
    param($Obj, [string]$FieldName, [string]$ContextLabel, $Violations)
    if ($Obj.PSObject.Properties.Name -notcontains $FieldName) { return }
    $value = $Obj.$FieldName
    if ($null -eq $value) { return }
    if ($value -isnot [array]) {
        $Violations.Add("$ContextLabel`: field '$FieldName' must be an array")
    }
}

function Get-CvfDefaultArtifactRegistryEntries {
    param([Parameter(Mandatory = $true)][string]$InitialHandoffRelative)

    return @(
        [ordered]@{ id = "schema-artifact-registry"; family = "schema"; path = "docs/catalog/schemas/ARTIFACT_REGISTRY.schema.json"; status = "ACTIVE"; description = "Closed schema reference for the Artifact Registry." }
        [ordered]@{ id = "schema-module-registry"; family = "schema"; path = "docs/catalog/schemas/MODULE_REGISTRY.schema.json"; status = "ACTIVE"; description = "Closed schema reference for the Module Registry." }
        [ordered]@{ id = "tool-catalog-manager"; family = "tool"; path = "scripts/manage_cvf_downstream_catalog.ps1"; status = "ACTIVE"; description = "Executable catalog manager (--check / --write)." }
        [ordered]@{ id = "tool-catalog-library"; family = "tool"; path = "scripts/lib/downstream_catalog/CvfDownstreamCatalogLib.ps1"; status = "ACTIVE"; description = "Standard-library catalog validation and rendering functions." }
        [ordered]@{ id = "manifest-cvf"; family = "manifest"; path = ".cvf/manifest.json"; status = "ACTIVE"; description = "CVF enforcement manifest." }
        [ordered]@{ id = "policy-cvf"; family = "policy"; path = ".cvf/policy.json"; status = "ACTIVE"; description = "CVF governance policy." }
        [ordered]@{ id = "continuity-session-memory"; family = "continuity"; path = "CVF_SESSION_MEMORY.md"; status = "ACTIVE"; description = "Project continuity front door." }
        [ordered]@{ id = "continuity-active-session-state"; family = "continuity"; path = "CVF_SESSION/ACTIVE_SESSION_STATE.json"; status = "ACTIVE"; description = "Active session/phase/role state." }
        [ordered]@{ id = "continuity-initial-handoff"; family = "continuity"; path = $InitialHandoffRelative; status = "ACTIVE"; description = "Initial agent handoff." }
        [ordered]@{ id = "truth-implementation-status"; family = "implementation_truth"; path = "IMPLEMENTATION_STATUS.json"; status = "ACTIVE"; description = "Machine implementation-truth surface." }
        [ordered]@{ id = "view-docs-index"; family = "generated_view"; path = "docs/INDEX.md"; status = "ACTIVE"; description = "Generated documentation index." }
        [ordered]@{ id = "view-module-catalog"; family = "generated_view"; path = "docs/catalog/MODULE_CATALOG.md"; status = "ACTIVE"; description = "Generated human module catalog." }
        [ordered]@{ id = "family-decisions"; family = "governed_artifact_family"; path = "docs/decisions"; status = "ACTIVE"; description = "Decisions." }
        [ordered]@{ id = "family-roadmaps"; family = "governed_artifact_family"; path = "docs/roadmaps"; status = "ACTIVE"; description = "Roadmaps." }
        [ordered]@{ id = "family-specs"; family = "governed_artifact_family"; path = "docs/specs"; status = "ACTIVE"; description = "Specifications." }
        [ordered]@{ id = "family-work-orders"; family = "governed_artifact_family"; path = "docs/work_orders"; status = "ACTIVE"; description = "Work orders." }
        [ordered]@{ id = "family-reviews"; family = "governed_artifact_family"; path = "docs/reviews"; status = "ACTIVE"; description = "Reviews and evidence." }
    )
}

function New-CvfArtifactRegistryObject {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectName,
        [Parameter(Mandatory = $true)][string]$DateStamp,
        [Parameter(Mandatory = $true)][string]$InitialHandoffRelative
    )
    return [ordered]@{
        schemaVersion = "1.0"
        projectName   = $ProjectName
        updatedAt     = $DateStamp
        claimBoundary = "Registers generated bootstrap authority surfaces only; it does not claim runtime module capability."
        artifacts     = @(Get-CvfDefaultArtifactRegistryEntries -InitialHandoffRelative $InitialHandoffRelative)
    }
}

function New-CvfModuleRegistryObject {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectName,
        [Parameter(Mandatory = $true)][string]$DateStamp
    )
    return [ordered]@{
        schemaVersion = "1.0"
        projectName   = $ProjectName
        updatedAt     = $DateStamp
        claimBoundary = "Empty initial registry; add only source-verified modules with evidence. No status may represent plan-only intent."
        modules       = @()
    }
}

function Test-CvfRelativeCatalogPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    if ($Path -match '\\') { return $false }
    if ($Path -match '^[A-Za-z]:') { return $false }
    if ($Path.StartsWith('/')) { return $false }
    $segments = $Path -split '/'
    foreach ($segment in $segments) {
        if ($segment -eq '..') { return $false }
    }
    return $true
}

function Test-CvfArtifactRegistry {
    param([Parameter(Mandatory = $true)]$Registry, [Parameter(Mandatory = $true)][string]$ProjectRoot)

    $violations = [System.Collections.Generic.List[string]]::new()
    $violations.AddRange([string[]](Test-CvfObjectShape -Obj $Registry -RequiredFields $Script:CvfArtifactRegistryTopLevelFields -AllowedFields $Script:CvfArtifactRegistryTopLevelFields -ContextLabel "artifact registry"))
    Test-CvfStringField -Obj $Registry -FieldName "projectName" -ContextLabel "artifact registry" -Violations $violations
    Test-CvfStringField -Obj $Registry -FieldName "claimBoundary" -ContextLabel "artifact registry" -Violations $violations
    if ($Registry.schemaVersion -ne "1.0") {
        $violations.Add("artifact registry: unsupported schemaVersion '$($Registry.schemaVersion)'")
    }
    if (($Registry.PSObject.Properties.Name -contains "artifacts") -and ($null -ne $Registry.artifacts) -and ($Registry.artifacts -isnot [array])) {
        $violations.Add("artifact registry: field 'artifacts' must be an array")
    }

    $seenIds = @{}
    $seenPaths = @{}
    foreach ($artifact in (ConvertTo-CvfSafeCollection $Registry.artifacts)) {
        $id = [string]$artifact.id
        $label = "artifact '$id'"
        $violations.AddRange([string[]](Test-CvfObjectShape -Obj $artifact -RequiredFields $Script:CvfArtifactEntryFields -AllowedFields $Script:CvfArtifactEntryFields -ContextLabel $label))
        Test-CvfStringField -Obj $artifact -FieldName "id" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $artifact -FieldName "family" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $artifact -FieldName "path" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $artifact -FieldName "status" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $artifact -FieldName "description" -ContextLabel $label -Violations $violations
        if ([string]::IsNullOrWhiteSpace($id) -or [string]::IsNullOrWhiteSpace([string]$artifact.path)) {
            continue
        }
        $path = [string]$artifact.path
        if ($seenIds.ContainsKey($id)) { $violations.Add("artifact registry: duplicate id '$id'") }
        $seenIds[$id] = $true
        if ($seenPaths.ContainsKey($path)) { $violations.Add("artifact registry: duplicate path '$path'") }
        $seenPaths[$path] = $true
        if (-not (Test-CvfRelativeCatalogPath $path)) {
            $violations.Add("$label`: path escape or non-portable path '$path'")
            continue
        }
        if ([string]::IsNullOrWhiteSpace([string]$artifact.family) -or [string]::IsNullOrWhiteSpace([string]$artifact.status)) {
            continue
        }
        if ($Script:CvfArtifactFamilies -notcontains $artifact.family) {
            $violations.Add("$label`: invalid family '$($artifact.family)'")
        }
        if ($Script:CvfArtifactStatuses -notcontains $artifact.status) {
            $violations.Add("$label`: invalid lifecycle status '$($artifact.status)'")
        }
        if ($artifact.family -ne "generated_view") {
            # generated_view existence/drift is validated separately by the
            # manager after rendering; requiring it here would make the very
            # first -Write run (which creates these files) impossible.
            $fullPath = Join-Path $ProjectRoot ($path -replace '/', '\')
            $isDirFamily = ($artifact.family -eq "governed_artifact_family")
            $exists = if ($isDirFamily) { Test-Path -LiteralPath $fullPath -PathType Container } else { Test-Path -LiteralPath $fullPath -PathType Leaf }
            if (-not $exists) {
                $violations.Add("$label`: registered path does not exist '$path'")
            }
        }
    }
    return , $violations.ToArray()
}

function Test-CvfArtifactRegistryBaseline {
    param([Parameter(Mandatory = $true)]$Registry, [Parameter(Mandatory = $true)][string]$InitialHandoffRelative)

    $violations = [System.Collections.Generic.List[string]]::new()
    $baseline = Get-CvfDefaultArtifactRegistryEntries -InitialHandoffRelative $InitialHandoffRelative
    $byId = @{}
    foreach ($artifact in (ConvertTo-CvfSafeCollection $Registry.artifacts)) { $byId[[string]$artifact.id] = $artifact }
    foreach ($expected in $baseline) {
        if (-not $byId.ContainsKey($expected.id)) {
            $violations.Add("artifact registry: missing mandatory authority surface '$($expected.id)'")
            continue
        }
        if ([string]$byId[$expected.id].path -ne $expected.path) {
            $violations.Add("artifact registry: mandatory authority surface '$($expected.id)' has unexpected path '$($byId[$expected.id].path)'")
        }
    }
    return , $violations.ToArray()
}

function Test-CvfModuleRegistry {
    param([Parameter(Mandatory = $true)]$Registry, [Parameter(Mandatory = $true)][string]$ProjectRoot)

    $violations = [System.Collections.Generic.List[string]]::new()
    $violations.AddRange([string[]](Test-CvfObjectShape -Obj $Registry -RequiredFields $Script:CvfModuleRegistryTopLevelFields -AllowedFields $Script:CvfModuleRegistryTopLevelFields -ContextLabel "module registry"))
    Test-CvfStringField -Obj $Registry -FieldName "projectName" -ContextLabel "module registry" -Violations $violations
    Test-CvfStringField -Obj $Registry -FieldName "claimBoundary" -ContextLabel "module registry" -Violations $violations
    if ($Registry.schemaVersion -ne "1.0") {
        $violations.Add("module registry: unsupported schemaVersion '$($Registry.schemaVersion)'")
    }
    if (($Registry.PSObject.Properties.Name -contains "modules") -and ($null -ne $Registry.modules) -and ($Registry.modules -isnot [array])) {
        $violations.Add("module registry: field 'modules' must be an array")
    }

    $modules = ConvertTo-CvfSafeCollection $Registry.modules
    $seenIds = @{}
    $seenPaths = @{}
    foreach ($m in $modules) {
        $id = [string]$m.id
        $label = "module '$id'"
        $violations.AddRange([string[]](Test-CvfObjectShape -Obj $m -RequiredFields $Script:CvfModuleEntryRequiredFields -AllowedFields $Script:CvfModuleEntryAllowedFields -ContextLabel $label))
        Test-CvfStringField -Obj $m -FieldName "id" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $m -FieldName "name" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $m -FieldName "path" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $m -FieldName "status" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $m -FieldName "description" -ContextLabel $label -Violations $violations
        Test-CvfStringField -Obj $m -FieldName "evidence" -ContextLabel $label -Violations $violations
        Test-CvfArrayField -Obj $m -FieldName "controls" -ContextLabel $label -Violations $violations
        Test-CvfArrayField -Obj $m -FieldName "dependencies" -ContextLabel $label -Violations $violations
        if ([string]::IsNullOrWhiteSpace($id) -or [string]::IsNullOrWhiteSpace([string]$m.path)) {
            continue
        }
        $path = [string]$m.path
        if ($seenIds.ContainsKey($id)) { $violations.Add("module registry: duplicate module id '$id'") }
        $seenIds[$id] = $true
        if ($seenPaths.ContainsKey($path)) { $violations.Add("module registry: duplicate module path '$path'") }
        $seenPaths[$path] = $true
        if (-not (Test-CvfRelativeCatalogPath $path)) {
            $violations.Add("$label`: path escape or non-portable path '$path'")
        }
        elseif (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot ($path -replace '/', '\')))) {
            $violations.Add("$label`: registered path does not exist '$path'")
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$m.status) -and ($Script:CvfModuleStatuses -notcontains $m.status)) {
            $violations.Add("$label`: invalid status '$($m.status)' (source-backed vocabulary only; plan-only statuses such as PLANNED are rejected)")
        }
        foreach ($control in @($m.controls)) {
            if (-not [string]::IsNullOrWhiteSpace($control) -and ($control -notmatch $Script:CvfControlPattern)) {
                $violations.Add("$label`: unknown CVF control token '$control'")
            }
        }
    }
    foreach ($m in $modules) {
        foreach ($dep in @($m.dependencies)) {
            if (-not [string]::IsNullOrWhiteSpace($dep) -and -not $seenIds.ContainsKey($dep)) {
                $violations.Add("module '$($m.id)': unknown module dependency '$dep'")
            }
        }
    }
    return , $violations.ToArray()
}

function Test-CvfRegistryProjectIdentity {
    # BSL-R2: the Artifact and Module registries must agree on which project
    # they describe.
    param([Parameter(Mandatory = $true)]$ArtifactRegistry, [Parameter(Mandatory = $true)]$ModuleRegistry)

    $violations = [System.Collections.Generic.List[string]]::new()
    $artifactProjectName = [string]$ArtifactRegistry.projectName
    $moduleProjectName = [string]$ModuleRegistry.projectName
    if (-not [string]::IsNullOrWhiteSpace($artifactProjectName) -and
        -not [string]::IsNullOrWhiteSpace($moduleProjectName) -and
        ($artifactProjectName -ne $moduleProjectName)) {
        $violations.Add("registry project identity mismatch: ARTIFACT_REGISTRY.json projectName '$artifactProjectName' != MODULE_REGISTRY.json projectName '$moduleProjectName'")
    }
    return , $violations.ToArray()
}

function Get-CvfCatalogState {
    # BSL-R1: classify catalog state before any catalog-kit write so bootstrap
    # never silently overwrites project-owned content.
    #
    # FRESH             - no governed source and no legacy/mixed signal; safe
    #                     to install the full kit.
    # ALREADY_GOVERNED  - docs/catalog/ARTIFACT_REGISTRY.json exists and is a
    #                     structurally valid governed source; safe to
    #                     regenerate views from it.
    # DAMAGED_GOVERNED  - docs/catalog/ARTIFACT_REGISTRY.json exists but does
    #                     not parse or fails the closed-schema shape check;
    #                     never write generated views from it.
    # LEGACY_OR_MIXED   - no governed source, but a pre-existing catalog-ish
    #                     surface (old MODULE_REGISTRY.json, docs/INDEX.md,
    #                     docs/catalog/MODULE_CATALOG.md, or a manager script)
    #                     is present; never mutate any catalog surface -
    #                     report migration-required instead.
    param([Parameter(Mandatory = $true)][string]$ProjectPath)

    $artifactRegistryPath = Join-Path $ProjectPath "docs\catalog\ARTIFACT_REGISTRY.json"
    $legacySignalPaths = @(
        (Join-Path $ProjectPath "docs\catalog\MODULE_REGISTRY.json"),
        (Join-Path $ProjectPath "docs\INDEX.md"),
        (Join-Path $ProjectPath "docs\catalog\MODULE_CATALOG.md"),
        (Join-Path $ProjectPath "scripts\manage_cvf_downstream_catalog.ps1")
    )
    $governedSourceExists = Test-Path -LiteralPath $artifactRegistryPath -PathType Leaf
    $anyLegacySignal = (@($legacySignalPaths | Where-Object { Test-Path -LiteralPath $_ })).Count -gt 0

    if (-not $governedSourceExists) {
        if ($anyLegacySignal) { return "LEGACY_OR_MIXED" }
        return "FRESH"
    }

    try {
        $artifactRegistry = Get-Content -LiteralPath $artifactRegistryPath -Raw -Encoding utf8 | ConvertFrom-Json
    }
    catch {
        return "DAMAGED_GOVERNED"
    }
    # [string[]](...) cast, not @(...): Test-CvfObjectShape returns via the
    # unary comma operator so a truly empty result survives plain/cast
    # capture as a real 0-length array; @() around that SAME call instead
    # treats the one comma-preserved pipeline object as a single element,
    # yielding a bogus 1-element (empty-string) "violation" and a false
    # DAMAGED_GOVERNED classification on every valid registry.
    $shapeViolations = [string[]](Test-CvfObjectShape -Obj $artifactRegistry -RequiredFields $Script:CvfArtifactRegistryTopLevelFields -AllowedFields $Script:CvfArtifactRegistryTopLevelFields -ContextLabel "artifact registry")
    if ($shapeViolations.Count -gt 0) { return "DAMAGED_GOVERNED" }
    return "ALREADY_GOVERNED"
}

function ConvertTo-CvfIndexMarkdown {
    param([Parameter(Mandatory = $true)]$Registry)

    $startHereFamilies = @("schema", "tool", "manifest", "policy", "continuity", "implementation_truth", "generated_view")
    $startHere = @($Registry.artifacts | Where-Object { $startHereFamilies -contains $_.family } | Sort-Object id)
    $families = @($Registry.artifacts | Where-Object { $_.family -eq "governed_artifact_family" } | Sort-Object id)

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add("# Project Documentation Index")
    $lines.Add("")
    $lines.Add("Machine-readable source: ``docs/catalog/ARTIFACT_REGISTRY.json``")
    $lines.Add("")
    $lines.Add("## Start Here")
    $lines.Add("")
    foreach ($a in $startHere) { $lines.Add("- $($a.description): ``$($a.path)``") }
    $lines.Add("")
    $lines.Add("## Governed Artifact Families")
    $lines.Add("")
    foreach ($a in $families) { $lines.Add("- $($a.description): ``$($a.path)/``") }
    $lines.Add("")
    $lines.Add("Plans describe intended work. ``IMPLEMENTATION_STATUS.json``, source, tests, and")
    $lines.Add("review evidence determine what is actually implemented.")
    $lines.Add("")
    return ($lines -join "`r`n")
}

function ConvertTo-CvfModuleCatalogMarkdown {
    param([Parameter(Mandatory = $true)]$Registry)

    $modules = @($Registry.modules | Sort-Object id)
    $total = $modules.Count
    $enforced = @($modules | Where-Object { $_.status -eq "ENFORCED" }).Count
    $partial = @($modules | Where-Object { $_.status -eq "PARTIAL" }).Count
    $contractOnly = @($modules | Where-Object { $_.status -eq "CONTRACT_ONLY" }).Count
    $stub = @($modules | Where-Object { $_.status -eq "STUB" }).Count
    $deprecated = @($modules | Where-Object { $_.status -eq "DEPRECATED" }).Count

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add("# Module Catalog")
    $lines.Add("")
    $lines.Add("Machine-readable source: ``docs/catalog/MODULE_REGISTRY.json``")
    $lines.Add("")
    $lines.Add("Status: $(if ($total -eq 0) { 'BOOTSTRAPPED_EMPTY' } else { 'GOVERNED' })")
    $lines.Add("")
    $lines.Add("## Metrics")
    $lines.Add("")
    $lines.Add("- Total modules: $total")
    $lines.Add("- Enforced: $enforced")
    $lines.Add("- Partial: $partial")
    $lines.Add("- Contract-only: $contractOnly")
    $lines.Add("- Stub: $stub")
    $lines.Add("- Deprecated: $deprecated")
    $lines.Add("")
    if ($total -eq 0) {
        $lines.Add("No modules have been source-verified and registered yet. Do not infer runtime")
        $lines.Add("capabilities from plans, handoffs, prompts, or provider-local memory.")
    }
    else {
        $lines.Add("| id | status | path | evidence | description |")
        $lines.Add("|---|---|---|---|---|")
        foreach ($m in $modules) {
            $lines.Add("| $($m.id) | $($m.status) | ``$($m.path)`` | $($m.evidence) | $($m.description) |")
        }
    }
    $lines.Add("")
    return ($lines -join "`r`n")
}
