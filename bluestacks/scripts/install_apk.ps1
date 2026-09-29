<#
.SYNOPSIS
Installs either the Original or Modded Shadow Fight 2 APK into BlueStacks,
and automatically pre-bundles the required 13.12 MB gamedata/asset packs
so the game never prompts for external content downloads on launch.

.PARAMETER Target
"original" or "modded" (default: "modded")
#>

param(
    [ValidateSet("original", "modded", "v1", "v2")]
    [string]$Target = "modded"
)

$HD_ADB = "C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
if (-not (Test-Path $HD_ADB)) {
    $HD_ADB = "adb"
}

if ($Target -eq "original") {
    $apkName = "SF2_OG.apk"
    $pkgName = "com.nekki.shadowfight"
} elseif ($Target -eq "v1") {
    $apkName = "SF2_Modded_v1.apk"
    $pkgName = "com.nekki.catblasters"
} elseif ($Target -eq "v2") {
    $apkName = "SF2_Modded_v2.apk"
    $pkgName = "com.nekki.catblasters"
} else {
    # Default 'modded': Prefer v2 if it exists, otherwise use v1
    $v2Path = Join-Path $PSScriptRoot "..\apks\SF2_Modded_v2.apk"
    if (Test-Path $v2Path) {
        $apkName = "SF2_Modded_v2.apk"
    } else {
        $apkName = "SF2_Modded_v1.apk"
    }
    $pkgName = "com.nekki.catblasters"
}
$apkPath = Join-Path $PSScriptRoot "..\apks\$apkName"
$gamedataPath = Join-Path $PSScriptRoot "..\..\modding\assets\downloaded_gamedata"

if (-not (Test-Path $apkPath)) {
    Write-Error "APK file not found: $apkPath"
    exit 1
}

Write-Host "=== Step 1: Connecting to BlueStacks ADB ===" -ForegroundColor Cyan
& $HD_ADB connect 127.0.0.1:5555
& $HD_ADB devices

Write-Host "`n=== Step 2: Installing $apkName ===" -ForegroundColor Yellow
& $HD_ADB -s 127.0.0.1:5555 install -r $apkPath

if ($LASTEXITCODE -ne 0) {
    # Fallback without -s flag if already uniquely identified
    & $HD_ADB install -r $apkPath
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[!] ADB install failed. Make sure ADB is enabled in BlueStacks: Settings -> Advanced -> Android Debug Bridge = ON." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 3: Pre-bundling 13.12 MB Gamedata Assets (Offline Content) ===" -ForegroundColor Cyan
if (Test-Path $gamedataPath) {
    $targetDir = "/sdcard/Android/data/$pkgName/files/gamedata"
    Write-Host "Creating target data directory: $targetDir" -ForegroundColor Gray
    & $HD_ADB shell "mkdir -p $targetDir"
    
    Write-Host "Pushing offline asset bundles (ANIMATIONS, VERSIONAL_CONFIGS)..." -ForegroundColor Yellow
    & $HD_ADB push "$gamedataPath\." "$targetDir/"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: Gamedata pre-loaded! The game will launch 100% offline with zero download prompts." -ForegroundColor Green
    } else {
        Write-Host "Warning: Could not push gamedata automatically. Launch game once to download or re-run script." -ForegroundColor Yellow
    }
}

Write-Host "`n=== Step 4: Configuring BlueStacks Keymappings ===" -ForegroundColor Cyan
$inputMapperDir = "C:\ProgramData\BlueStacks_nxt\Engine\UserData\InputMapper"
if (Test-Path $inputMapperDir) {
    $cfgSrc = Join-Path $PSScriptRoot "..\configs\com.nekki.catblasters.cfg"
    if (Test-Path $cfgSrc) {
        Copy-Item -Force $cfgSrc "$inputMapperDir\com.nekki.catblasters.cfg"
        Copy-Item -Force $cfgSrc "$inputMapperDir\UserFiles\com.nekki.catblasters.cfg"
        Write-Host "SUCCESS: Keymappings installed (WASD for movement, J for punch, K for kick)." -ForegroundColor Green
    }
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "Installation Complete! Launch '$apkName' in BlueStacks." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
