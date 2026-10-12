@echo off
:: ============================================================================
:: AUTOSAR HLD Intelligence Assistant - Docker Logs Viewer
:: ============================================================================

echo.
echo Following container logs (Press Ctrl+C to exit)...
echo.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

cd /d "%PROJECT_ROOT%"

docker compose logs -f
