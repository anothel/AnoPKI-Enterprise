# SPDX-License-Identifier: MPL-2.0
param(
    [string]$CommunityRemote = "community",
    [string]$CommunityBranch = "main",
    [string]$CommunityUrl = "",
    [switch]$ConfigureRemote,
    [switch]$Fetch
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
        Write-Warning "Worktree has local changes. Review them before integrating Community updates."
        $status | ForEach-Object { Write-Host $_ }
    }

    Write-Host "Remote check: git remote get-url $CommunityRemote"
    $remoteUrl = & git config --get "remote.$CommunityRemote.url"
    if ($LASTEXITCODE -ne 0) {
        if (-not $ConfigureRemote) {
            Write-Host "Missing remote '$CommunityRemote'. Configure it with:"
            Write-Host "  git remote add $CommunityRemote <community-url-or-local-path>"
        }
        elseif ([string]::IsNullOrWhiteSpace($CommunityUrl)) {
            throw "Pass -CommunityUrl when using -ConfigureRemote"
        }
        else {
            Invoke-Git @("remote", "add", $CommunityRemote, $CommunityUrl)
            $remoteUrl = $CommunityUrl
        }
    }

    if ($remoteUrl) {
        Write-Host "Community remote: $CommunityRemote -> $remoteUrl"
    }

    if ($Fetch) {
        Invoke-Git @("fetch", $CommunityRemote, $CommunityBranch)
    }
    else {
        Write-Host "Fetch preview:"
        Write-Host "  git fetch $CommunityRemote $CommunityBranch"
    }

    Write-Host ""
    Write-Host "Review after fetch:"
    Write-Host "  git log --oneline HEAD..$CommunityRemote/$CommunityBranch"
    Write-Host "  git diff --stat HEAD...$CommunityRemote/$CommunityBranch"
    Write-Host "  git diff --name-status HEAD...$CommunityRemote/$CommunityBranch"
    Write-Host ""
    Write-Host "Manual integration command is documented in docs\enterprise\upstream-sync.md."
    Write-Host ""
    Write-Host "Required post-sync checks:"
    Write-Host "  python scripts\validate-enterprise-boundary.py"
    Write-Host "  python scripts\validate-docs.py"
    Write-Host "  python scripts\test_sync_community_upstream.py"
}
finally {
    Pop-Location
}
