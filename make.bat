@echo off
setlocal

REM Find virtual environment python or system python
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

if "%1"=="" goto all
if /I "%1"=="install" goto install
if /I "%1"=="boot" goto boot
if /I "%1"=="all" goto all
if /I "%1"=="reinstall" goto reinstall
if /I "%1"=="restart" goto restart
if /I "%1"=="status" goto status
if /I "%1"=="screenshot" goto screenshot
if /I "%1"=="help" goto help

echo [Error] Unknown target: %1
goto help

:install
%PYTHON% scripts/install.py %2 %3 %4
goto end

:boot
%PYTHON% scripts/boot.py %2 %3 %4
goto end

:all
%PYTHON% scripts/install.py
if errorlevel 1 goto end
%PYTHON% scripts/boot.py
goto end

:reinstall
%PYTHON% scripts/install.py --force
goto end

:restart
%PYTHON% scripts/boot.py --restart
goto end

:screenshot
%PYTHON% .agents/skills/bluestacks-instant-screenshot/scripts/screenshot.py --artifact current_screen
goto end

:status
%PYTHON% -c "from scripts.common import is_installed, is_running, find_adb, get_connected_device; adb = find_adb(); dev = get_connected_device(adb); print(f'ADB Device : {dev}'); print(f'Installed  : {is_installed()}'); print(f'Running    : {is_running()}')"
goto end

:help
echo.
echo Shadow Fight 2 Automation Harness
echo ==================================
echo Usage:
echo   make install     - Check installation; install SF2_Modded_v3.apk if missing
echo   make boot        - Check installation; boot the game on BlueStacks
echo   make all         - Run install, then boot (default)
echo   make reinstall   - Force reinstall the APK
echo   make restart     - Force stop and reboot the game
echo   make screenshot  - Instant sub-second screen capture to artifacts
echo   make status      - Check device, installation, and running status
echo.

:end
endlocal
