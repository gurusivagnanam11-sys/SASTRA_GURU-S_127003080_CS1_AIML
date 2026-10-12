@echo off
:: ============================================================================
:: AUTOSAR HLD Intelligence Assistant - Docker Smoke Test
:: ============================================================================

echo.
echo ===================================================
echo Running Docker Deployment Smoke Tests...
echo ===================================================
echo.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

cd /d "%PROJECT_ROOT%"

python scripts\docker_smoke_test.py
if errorlevel 1 (
    echo.
    echo [ERROR] Smoke test reported failures.
    exit /b 1
)

echo.
echo [SUCCESS] All Docker smoke tests passed.
echo.
