@echo off
setlocal

REM Find virtual environment python or system python
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

if "%1"=="" goto frida
if /I "%1"=="frida" goto frida
if /I "%1"=="frida-watch" goto frida_watch
if /I "%1"=="status" goto status
if /I "%1"=="screenshot" goto screenshot
if /I "%1"=="help" goto help

echo [Error] Unknown target: %1
goto help

:frida
%PYTHON% scripts/start_frida_service.py %2 %3 %4
goto end

:frida_watch
%PYTHON% scripts/start_frida_service.py --watch %2 %3 %4
goto end

:screenshot
%PYTHON% .agents/skills/bluestacks-instant-screenshot/scripts/screenshot.py --artifact current_screen
goto end

:status
%PYTHON% -c "from scripts.start_frida_service import find_adb, get_connected_device, is_app_running, DEFAULT_PACKAGE; adb = find_adb(); dev = get_connected_device(adb); run, pid = is_app_running(adb, dev, DEFAULT_PACKAGE) if dev else (False, None); print(f'ADB Device : {dev}'); print(f'App Running: {run} (PID: {pid})')"
goto end

:help
echo.
echo Shadow Fight 2 Automation Harness
echo ==================================
echo Usage:
echo   .\make.bat frida       - Verify and establish Frida bridge ^& port forwarding
echo   .\make.bat frida-watch - Run continuous Frida connection watchdog daemon
echo   .\make.bat screenshot  - Instant sub-second screen capture to artifacts
echo   .\make.bat status      - Check device, installation, and running status
echo.

:end
endlocal
