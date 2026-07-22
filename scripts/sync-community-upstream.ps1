# SPDX-License-Identifier: MPL-2.0
param(
    [string]$CommunityRemote = "community",
    [string]$CommunityBranch = "main",
    [string]$CommunityUrl = "",
    [string]$TargetCommit = "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc",
    [string]$PreviousBaseline = "acb71b8f4e9133d9c25dad1be3bca58209fba0d7",
    [switch]$ConfigureRemote,
    [switch]$Fetch,
    [switch]$Verify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")

function Invoke-Git {
    param([string[]]$Arguments)

    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($null -eq (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git executable not found"
}

if ($TargetCommit -cnotmatch '^[0-9a-f]{40}$') {
    throw "TargetCommit must be an exact lowercase 40-character SHA"
}
if ($PreviousBaseline -cnotmatch '^[0-9a-f]{40}$') {
    throw "PreviousBaseline must be an exact lowercase 40-character SHA"
}
if ($TargetCommit -ceq $PreviousBaseline) {
    throw "TargetCommit must not reuse the stale previous baseline"
}

Push-Location -LiteralPath $RepoRoot
try {
    Write-Host "Repository: $RepoRoot"
    Write-Host "Status check: git status --short"
    $status = & git status --short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    if ($status) {
        Write-Warning "Worktree has local changes. This helper is read-only and will not alter them."
        $status | ForEach-Object { Write-Host $_ }
    }

    Write-Host "Remote check: git remote get-url $CommunityRemote"
    $remoteUrl = & git config --get "remote.$CommunityRemote.url"
    if ($LASTEXITCODE -ne 0) {
        if (-not $ConfigureRemote) {
            throw "Missing remote '$CommunityRemote'"
        }
        if ([string]::IsNullOrWhiteSpace($CommunityUrl)) {
            throw "Pass -CommunityUrl when using -ConfigureRemote"
        }
        Invoke-Git @("remote", "add", $CommunityRemote, $CommunityUrl)
        $remoteUrl = $CommunityUrl
    }
    Write-Host "Community remote: $CommunityRemote -> $remoteUrl"

    if ($Fetch) {
        Invoke-Git @("fetch", $CommunityRemote, $CommunityBranch)
    }
    else {
        Write-Host "Fetch preview: git fetch $CommunityRemote $CommunityBranch"
    }

    Invoke-Git @("cat-file", "-e", "$TargetCommit`^{commit}")
    Write-Host "Pinned target commit: $TargetCommit"
    Invoke-Git @("show", "-s", "--format=%H %s", $TargetCommit)

    Write-Host "Exact baseline diff:"
    Invoke-Git @("diff", "--name-status", $PreviousBaseline, $TargetCommit)
    Write-Host "Shared files must be extracted from the pinned target tree; mixed files require reviewed manual integration."

    if ($Verify) {
        & python scripts\validate-community-baseline.py
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    else {
        Write-Host "Post-sync verification: python scripts\validate-community-baseline.py"
    }
}
finally {
    Pop-Location
}
