@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

%PYTHON% scripts/start_frida_service.py %*

if "%1"=="" (
    if errorlevel 1 (
        echo.
        echo Press any key to exit...
        pause >nul
    )
)
endlocal
