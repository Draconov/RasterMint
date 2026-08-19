# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

$ErrorActionPreference = "Stop"

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

& $Python -m pip install -e ".[build]"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed with exit code $LASTEXITCODE" }

& $Python -m PyInstaller build\rastermint.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

if (-not (Test-Path "dist\RasterMint.exe")) {
    throw "PyInstaller did not create dist\RasterMint.exe"
}

if (Test-Path "release") { Remove-Item "release" -Recurse -Force }
New-Item -ItemType Directory -Force -Path "release" | Out-Null

Copy-Item "dist\RasterMint.exe" "release\RasterMint.exe"

$SizeMiB = [Math]::Round((Get-Item "release\RasterMint.exe").Length / 1MB, 1)
Write-Host "Built release\RasterMint.exe ($SizeMiB MiB)"
