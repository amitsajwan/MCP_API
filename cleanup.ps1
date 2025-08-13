# =========================
# cleanup_unused.ps1
# Safely remove deprecated/legacy files from simplified MCP project
# Default: dry run (no deletions). Use -Execute to actually delete.
# Optional: -CreateBackup to zip current tree before deletion.
# =========================

param(
    [switch]$Execute,
    [switch]$CreateBackup,
    [string]$BackupName = "pre_cleanup_backup.zip"
)

$ErrorActionPreference = "Stop"

Write-Host "== OpenAPI MCP Cleanup Script ==" -ForegroundColor Cyan
if ($Execute) {
    Write-Host "Mode: EXECUTE (will delete)" -ForegroundColor Yellow
} else {
    Write-Host "Mode: DRY RUN (no files deleted)" -ForegroundColor Yellow
}

# 1. Explicit backend/demo legacy targets
$legacyFiles = @(
    "mcp_client.py",
    "mcp_server.py",
    "mcp_server_api.py",
    "openapi.py",
    "demo_queries.py",
    "example_usage.py",
    "login_flow.py",
    "mcp_client_test.py"
)

# 2. Legacy React console components (keep only SimpleChatApp + simple.css)
$uiFolder = "frontend\\src\\ui"
$keepUI = @("SimpleChatApp.tsx", "simple.css")
$legacyUI = @()
if (Test-Path $uiFolder) {
    Get-ChildItem -Path $uiFolder -File | Where-Object {
        $_.Name -notin $keepUI -and ($_.Extension -in ".tsx", ".css", ".ts")
    } | ForEach-Object {
        $legacyUI += (Join-Path $uiFolder $_.Name)
    }
}

# Combine
$targets = @()
$legacyFiles | ForEach-Object {
    $p = Join-Path (Get-Location) $_
    if (Test-Path $p) { $targets += $p }
}
$legacyUI | ForEach-Object {
    $p = Join-Path (Get-Location) $_
    if (Test-Path $p) { $targets += $p }
}

if (-not $targets) {
    Write-Host "No target files found to remove." -ForegroundColor Green
    exit 0
}

Write-Host "`nPlanned removals (`$targets):" -ForegroundColor Cyan
$targets | ForEach-Object { Write-Host "  - $_" }

# Optional backup
if ($CreateBackup) {
    if (Test-Path $BackupName) {
        Write-Host "Backup $BackupName already exists. Aborting to avoid overwrite." -ForegroundColor Red
        exit 1
    }
    Write-Host "`nCreating backup archive: $BackupName ..."
    Compress-Archive -Path * -DestinationPath $BackupName -Force
    Write-Host "Backup created."
}

if (-not $Execute) {
    Write-Host "`nDry run complete. Re-run with -Execute to actually delete." -ForegroundColor Yellow
    Write-Host "Example:  powershell -ExecutionPolicy Bypass -File .\\cleanup_unused.ps1 -Execute -CreateBackup"
    exit 0
}

Write-Host "`nDeleting files..." -ForegroundColor Red
$failed = @()
foreach ($f in $targets) {
    try {
        Remove-Item -Path $f -Force
        Write-Host "Removed $f"
    } catch {
        Write-Host "Failed to remove $f : $_" -ForegroundColor Red
        $failed += $f
    }
}

# If repo is git, stage deletions
if (Test-Path ".git") {
    Write-Host "`nStaging deletions in git..."
    foreach ($f in $targets) {
        if (-not (Test-Path $f)) {
            git rm -f --cached $f 2>$null | Out-Null
        }
    }
    git add . | Out-Null
    Write-Host "Git staging done. Commit manually:"
    Write-Host "  git commit -m 'chore: remove legacy and deprecated files'"
}

if ($failed.Count -eq 0) {
    Write-Host "`nCleanup finished successfully." -ForegroundColor Green
} else {
    Write-Host "`nCleanup finished with failures on:" -ForegroundColor Yellow
    $failed | ForEach-Object { Write-Host "  - $_" }
}
