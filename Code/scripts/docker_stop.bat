@echo off
:: ============================================================================
:: AUTOSAR HLD Intelligence Assistant - Docker Stopper
:: ============================================================================

echo.
echo ===================================================
echo Stopping AUTOSAR HLD Docker Containers...
echo ===================================================
echo.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

cd /d "%PROJECT_ROOT%"

docker compose down

echo.
echo [SUCCESS] Containers stopped.
echo.
