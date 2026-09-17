[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [ValidateSet("beta", "prod")]
    [string]$Channel = "beta",

    [ValidateSet("windows-x86_64", "darwin-aarch64", "darwin-x86_64")]
    [string]$Platform = "windows-x86_64",

    [ValidateSet("jdcloud", "minio")]
    [string]$UploadProvider = "jdcloud",

    [switch]$NoUpload,
    [switch]$DryRunUpload,
    [switch]$PrintOnly,
    [switch]$CreateTag,
    [string]$TagName,
    [switch]$PushTag,
    [switch]$SkipInstaller,
    [string]$Notes,
    [string]$NotesFile,
    [switch]$AutoNotes,
    [switch]$NoAutoNotes,
    [string]$RequiredBranch = "",
    [switch]$AllowVersionChannelMismatch
)

$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -lt 6) {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    $OutputEncoding = New-Object System.Text.UTF8Encoding $false
}

$currentBranch = (git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($currentBranch)) {
    throw "Cannot determine current git branch. Refusing to package."
}

$allowedBranches = if ($Channel -eq "prod") { @("release") } else { @("test", "release") }
if ($currentBranch -notin $allowedBranches) {
    if ($Channel -eq "prod") {
        throw "Prod packaging is only allowed on branch 'release'. Current branch is '$currentBranch'."
    }
    throw "Beta packaging is only allowed on branches 'test' or 'release'. Current branch is '$currentBranch'."
}

if (-not [string]::IsNullOrWhiteSpace($RequiredBranch)) {
    if ($RequiredBranch -notin $allowedBranches) {
        throw "-RequiredBranch '$RequiredBranch' is not allowed for channel '$Channel'."
    }
    if ($currentBranch -ne $RequiredBranch) {
        throw "Packaging was restricted to branch '$RequiredBranch'. Current branch is '$currentBranch'."
    }
}

if ($Channel -eq "beta" -and $Version -notmatch "-beta\.") {
    if (-not $AllowVersionChannelMismatch) {
        throw "Beta channel requires a prerelease version such as 1.1.8-beta.1. Pass -AllowVersionChannelMismatch to override."
    }
}

if ($Channel -eq "prod" -and $Version -match "-") {
    if (-not $AllowVersionChannelMismatch) {
        throw "Prod channel should use a stable version such as 1.1.8. Pass -AllowVersionChannelMismatch to override."
    }
}

function Get-AutoReleaseNotes {
    $latestTag = (git describe --tags --abbrev=0 2>$null)
    $latestTag = if ($LASTEXITCODE -eq 0) { $latestTag.Trim() } else { "" }
    $logArgs = @("log", "--no-merges", "--pretty=format:- %s")
    $rangeLabel = "last 20 commits"
    if (-not [string]::IsNullOrWhiteSpace($latestTag)) {
        $logArgs += "${latestTag}..HEAD"
        $rangeLabel = "${latestTag}..HEAD"
    } else {
        $logArgs += "-20"
    }

    $items = (& git @logArgs) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    if (-not $items -or $items.Count -eq 0) {
        $items = @("- Stability improvements.")
    }

    return "### Changes`n$($items -join "`n")`n`nRange: $rangeLabel"
}

if (-not [string]::IsNullOrWhiteSpace($Notes) -and -not [string]::IsNullOrWhiteSpace($NotesFile)) {
    throw "Pass only one of -Notes or -NotesFile."
}

$resolvedNotes = ""
if (-not [string]::IsNullOrWhiteSpace($NotesFile)) {
    $resolvedNotes = (Get-Content -LiteralPath $NotesFile -Encoding UTF8 -Raw).Trim()
} elseif (-not [string]::IsNullOrWhiteSpace($Notes)) {
    $resolvedNotes = $Notes.Trim()
} elseif ($AutoNotes -or -not $NoAutoNotes) {
    $resolvedNotes = Get-AutoReleaseNotes
}

$prefix = "bytecp-plus/$Channel"
$resolvedTagName = if ([string]::IsNullOrWhiteSpace($TagName)) { "v$Version" } else { $TagName.Trim() }
$buildModeSuffix = if ($Channel -eq "prod") { ":pro" } else { ":beta" }
$npmScript = if ($Platform -eq "windows-x86_64") {
    "tauri:build:upload:updater:win$buildModeSuffix"
} else {
    "tauri:build:upload:updater:mac$buildModeSuffix"
}

$npmArgs = @(
    "run",
    $npmScript,
    "--",
    "--release-version=$Version",
    "--platform",
    $Platform,
    "--upload-provider=$UploadProvider"
)

if ($Platform -ne "windows-x86_64" -and $SkipInstaller) {
    $npmArgs += "--bundles=app"
}

if ($NoUpload) {
    $npmArgs += "--no-upload"
}

if ($DryRunUpload) {
    $npmArgs += "--dry-run-upload"
}

$npmArgs += @(
    "--upload-args",
    "--prefix=$prefix",
    "--platform=$Platform"
)

if ($Platform -ne "windows-x86_64" -and $SkipInstaller) {
    $npmArgs += "--skip-installer"
}

if (-not [string]::IsNullOrWhiteSpace($resolvedNotes)) {
    $npmArgs += "--notes=$resolvedNotes"
}

$display = "npm " + ($npmArgs -join " ")
Write-Host "[release-packaging] channel=$Channel version=$Version platform=$Platform prefix=$prefix"
Write-Host "[release-packaging] branch=$currentBranch"
if (-not [string]::IsNullOrWhiteSpace($resolvedNotes)) {
    Write-Host "[release-packaging] notes:"
    Write-Host $resolvedNotes
}
Write-Host "[release-packaging] $display"
if ($CreateTag) {
    Write-Host "[release-packaging] tag=$resolvedTagName pushTag=$PushTag"
}

if ($PrintOnly) {
    exit 0
}

& npm @npmArgs
$buildExitCode = $LASTEXITCODE
if ($buildExitCode -ne 0) {
    exit $buildExitCode
}

if ($CreateTag) {
    $existingTagCommit = $null
    git rev-parse -q --verify "refs/tags/$resolvedTagName" *> $null
    if ($LASTEXITCODE -eq 0) {
        $existingTagCommit = (git rev-list -n 1 $resolvedTagName).Trim()
        $headCommit = (git rev-parse HEAD).Trim()
        if ($existingTagCommit -eq $headCommit) {
            Write-Host "[release-packaging] tag already exists on HEAD: $resolvedTagName"
        } else {
            throw "Tag $resolvedTagName already exists on another commit. Refusing to move it."
        }
    } else {
        git tag -a $resolvedTagName -m "Release $Version ($Channel)"
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
        Write-Host "[release-packaging] created tag $resolvedTagName"
    }

    if ($PushTag) {
        git push origin $resolvedTagName
        exit $LASTEXITCODE
    }
}

exit 0
