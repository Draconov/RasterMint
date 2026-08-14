$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
& $Python -m pip install -e ".[build]"
& $Python -m PyInstaller build\rastermint.spec --noconfirm --clean

New-Item -ItemType Directory -Force -Path release | Out-Null
$Zip = "release\RasterMint-windows-x64.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path "dist\RasterMint\*" -DestinationPath $Zip -CompressionLevel Optimal
Write-Host "Built $Zip"
