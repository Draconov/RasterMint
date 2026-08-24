# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

$ErrorActionPreference = "Stop"
# We handle native-process exit codes explicitly so an optional lean-FFmpeg
# failure can fall back cleanly for local builds.
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

& $Python -m pip install -e ".[build]"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed with exit code $LASTEXITCODE" }

function Get-ImageioFfmpegPath {
    $value = (& $Python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())" | Select-Object -Last 1)
    if ($LASTEXITCODE -ne 0 -or -not $value) { return $null }
    return $value.Trim()
}

function Test-RasterMintFfmpeg([string]$Candidate) {
    if (-not $Candidate -or -not (Test-Path $Candidate -PathType Leaf)) {
        return $false
    }

    Write-Host "Validating lean RasterMint FFmpeg: $Candidate"
    & $Python "scripts\validate_ffmpeg.py" $Candidate
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Lean FFmpeg failed RasterMint's codec/media smoke tests."
        return $false
    }

    # The whole point of this build is faster one-file extraction. Do not
    # replace imageio's executable unless the validated candidate is smaller.
    $Reference = Get-ImageioFfmpegPath
    if ($Reference -and (Test-Path $Reference -PathType Leaf)) {
        $CandidateBytes = (Get-Item $Candidate).Length
        $ReferenceBytes = (Get-Item $Reference).Length
        if ($CandidateBytes -ge $ReferenceBytes) {
            $CandidateMiB = [Math]::Round($CandidateBytes / 1MB, 1)
            $ReferenceMiB = [Math]::Round($ReferenceBytes / 1MB, 1)
            Write-Warning "Lean FFmpeg is not smaller ($CandidateMiB MiB vs imageio $ReferenceMiB MiB); keeping the known-good imageio binary."
            return $false
        }
        $SavedMiB = [Math]::Round(($ReferenceBytes - $CandidateBytes) / 1MB, 1)
        Write-Host "Lean FFmpeg saves $SavedMiB MiB inside the one-file payload before compression."
    }
    return $true
}

function Find-VcpkgExecutable {
    $Candidates = @()
    if ($env:VCPKG_ROOT) {
        $Candidates += (Join-Path $env:VCPKG_ROOT "vcpkg.exe")
    }
    if ($env:VCPKG_INSTALLATION_ROOT) {
        $Candidates += (Join-Path $env:VCPKG_INSTALLATION_ROOT "vcpkg.exe")
    }
    $Command = Get-Command "vcpkg.exe" -ErrorAction SilentlyContinue
    if ($Command) {
        $Candidates += $Command.Source
    }
    $Command = Get-Command "vcpkg" -ErrorAction SilentlyContinue
    if ($Command) {
        $Candidates += $Command.Source
    }

    foreach ($Candidate in ($Candidates | Select-Object -Unique)) {
        if ($Candidate -and (Test-Path $Candidate -PathType Leaf)) {
            return $Candidate
        }
    }
    return $null
}

function Build-LeanFfmpeg {
    $Vcpkg = Find-VcpkgExecutable
    if (-not $Vcpkg) {
        Write-Warning "vcpkg was not found; Windows build will use imageio-ffmpeg's bundled executable."
        return $null
    }

    $ManifestRoot = Join-Path $Root "build\ffmpeg-vcpkg"
    $WorkRoot = Join-Path $Root "build\ffmpeg-vcpkg\work"
    $InstallRoot = Join-Path $WorkRoot "installed"
    $BuildTrees = Join-Path $WorkRoot "buildtrees"
    $Packages = Join-Path $WorkRoot "packages"
    $Downloads = Join-Path $WorkRoot "downloads"

    New-Item -ItemType Directory -Force -Path $InstallRoot, $BuildTrees, $Packages, $Downloads | Out-Null

    Write-Host "Building/restoring RasterMint's lean static FFmpeg with vcpkg..."
    # Manifest features intentionally keep FFmpeg's native codec/demuxer set,
    # but omit large unrelated external libraries. x264 supplies RasterMint's
    # H.264 MP4 encoder; zlib is retained for the PNG-frame GIF export path.
    & $Vcpkg install `
        "--x-manifest-root=$ManifestRoot" `
        "--x-install-root=$InstallRoot" `
        "--x-buildtrees-root=$BuildTrees" `
        "--x-packages-root=$Packages" `
        "--downloads-root=$Downloads" `
        "--triplet=x64-windows-static"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "vcpkg could not build the lean FFmpeg (exit $LASTEXITCODE)."
        return $null
    }

    $Expected = Join-Path $InstallRoot "x64-windows-static\tools\ffmpeg\ffmpeg.exe"
    if (Test-Path $Expected -PathType Leaf) {
        return $Expected
    }

    $Found = Get-ChildItem $InstallRoot -Recurse -Filter "ffmpeg.exe" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch "[\\/]debug[\\/]" } |
        Select-Object -First 1
    if ($Found) { return $Found.FullName }
    Write-Warning "vcpkg completed but no release ffmpeg.exe was found."
    return $null
}

$LeanFfmpeg = $null
if ($env:RASTERMINT_FFMPEG_EXE) {
    if (Test-RasterMintFfmpeg $env:RASTERMINT_FFMPEG_EXE) {
        $LeanFfmpeg = (Resolve-Path $env:RASTERMINT_FFMPEG_EXE).Path
    } else {
        Write-Warning "Ignoring invalid RASTERMINT_FFMPEG_EXE override."
    }
}

if (-not $LeanFfmpeg) {
    try {
        $Candidate = Build-LeanFfmpeg
        if ($Candidate -and (Test-RasterMintFfmpeg $Candidate)) {
            $LeanFfmpeg = (Resolve-Path $Candidate).Path
        }
    } catch {
        Write-Warning "Lean FFmpeg preparation failed: $($_.Exception.Message)"
    }
}

if ($LeanFfmpeg) {
    $env:RASTERMINT_FFMPEG_EXE = $LeanFfmpeg
    Write-Host "PyInstaller will bundle lean FFmpeg: $LeanFfmpeg"
} else {
    Remove-Item Env:RASTERMINT_FFMPEG_EXE -ErrorAction SilentlyContinue
    # Lean FFmpeg is an optimization, never a release prerequisite. vcpkg can
    # fail transiently or change upstream; RasterMint must still ship with the
    # known-good imageio-ffmpeg executable rather than fail all platform CI.
    Write-Warning "Lean FFmpeg is unavailable; falling back to imageio-ffmpeg's known-good executable."
}

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
