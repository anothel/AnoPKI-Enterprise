# SPDX-License-Identifier: MPL-2.0
param(
    [string]$CommunityRemote = "community",
    [string]$CommunityBranch = "main",
    [string]$CommunityUrl = "",
    [string]$TargetCommit = "96297b14d2f681b75861032d9871a41d6e689c78",
    [string]$PreviousBaseline = "ae3ddee72dd05f274b9bbae1b514cdc4c4de03f5",
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
