<#
.SYNOPSIS
    Boot the ICE dev stack from a space-free path (Docker Desktop / WSL2 workaround).

.DESCRIPTION
    Docker Desktop's WSL2 backend mis-translates bind-mount source paths that
    contain spaces (it splits the path at the first space and fails with
    "mkdir /run/desktop/mnt/host/d: file exists"). The real repo lives at
    "D:\Genesys_Systems\Interactive Cirriculum Engine", which has spaces.

    This script routes docker compose through a space-free NTFS junction
    (D:\ice -> the real repo) so every relative bind mount (../../, ./...)
    resolves to a space-free host path. It creates the junction on first run
    if it is missing, then runs compose from inside the junction.

.PARAMETER Action
    Compose action to run: up (default), down, logs, restart, ps.

.EXAMPLE
    .\dev.ps1              # start the stack detached
    .\dev.ps1 down         # stop the stack
    .\dev.ps1 logs         # tail logs
#>
[CmdletBinding()]
param(
    [ValidateSet("up", "down", "logs", "restart", "ps")]
    [string]$Action = "up"
)

$ErrorActionPreference = "Stop"

# The space-free junction and the real (spaced) repo it must point at.
$JunctionPath = "D:\ice"
$RealRepoPath = "D:\Genesys_Systems\Interactive Cirriculum Engine"
$ComposeFile  = "infra/compose/docker-compose.dev.yml"

function Test-IsJunction {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return $item.LinkType -eq "Junction"
}

# --- Ensure the junction exists and points at the right place --------------
if (Test-IsJunction -Path $JunctionPath) {
    $target = (Get-Item -LiteralPath $JunctionPath -Force).Target
    if ($target -ne $RealRepoPath) {
        Write-Warning "Junction $JunctionPath points at '$target', expected '$RealRepoPath'. Recreating."
        cmd /c rmdir "$JunctionPath" | Out-Null
        cmd /c mklink /J "$JunctionPath" "$RealRepoPath" | Out-Null
    }
}
elseif (Test-Path -LiteralPath $JunctionPath) {
    throw "$JunctionPath already exists and is NOT a junction. Remove or rename it, then re-run."
}
else {
    Write-Host "Creating junction $JunctionPath -> $RealRepoPath" -ForegroundColor Cyan
    cmd /c mklink /J "$JunctionPath" "$RealRepoPath" | Out-Null
}

# --- Run compose from inside the space-free junction -----------------------
Push-Location -LiteralPath $JunctionPath
try {
    switch ($Action) {
        "up"      { docker compose -f $ComposeFile up -d }
        "down"    { docker compose -f $ComposeFile down }
        "logs"    { docker compose -f $ComposeFile logs -f --tail=200 }
        "restart" { docker compose -f $ComposeFile restart }
        "ps"      { docker compose -f $ComposeFile ps }
    }
}
finally {
    Pop-Location
}
