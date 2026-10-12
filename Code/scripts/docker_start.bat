@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: AUTOSAR HLD Intelligence & Traceability Assistant - Docker Launcher
:: ============================================================================
:: Builds and starts the containerized application (hld-api and hld-ui).
:: CPU-only execution with Gemini Cloud LLM integration.
:: ============================================================================

echo.
echo ===================================================
echo AUTOSAR HLD Assistant - Docker Deployment Launcher
echo ===================================================
echo.

:: Detect Project Root relative to script location
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

cd /d "%PROJECT_ROOT%"

:: 1. Verify Docker CLI is available
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker command not found.
    echo Please ensure Docker Desktop is installed and added to your system PATH.
    echo Download from: https://www.docker.com/products/docker-desktop/
    goto :ERROR_EXIT
)

:: 2. Verify Docker daemon is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running.
    echo Please start Docker Desktop and wait until the engine is running before launching.
    goto :ERROR_EXIT
)

:: 3. Verify .env file exists and GEMINI_API_KEY is present
if not exist "%PROJECT_ROOT%\.env" (
    echo [WARNING] .env file not found. Copying from .env.example...
    copy "%PROJECT_ROOT%\.env.example" "%PROJECT_ROOT%\.env" >nul
    echo [ACTION REQUIRED] Please configure your GEMINI_API_KEY inside "%PROJECT_ROOT%\.env" before continuing.
    goto :ERROR_EXIT
)

findstr /I "GEMINI_API_KEY=" "%PROJECT_ROOT%\.env" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] GEMINI_API_KEY was not found in .env.
    echo The Docker container uses Gemini Cloud for LLM inference.
    echo Please add GEMINI_API_KEY to your .env file.
)

:: 4. Build and start containers
echo [INFO] Building and starting containers with Docker Compose...
docker compose up --build -d
if errorlevel 1 (
    echo [ERROR] Docker compose failed to start services.
    goto :ERROR_EXIT
)

echo.
echo ===================================================
echo [SUCCESS] Containers started successfully!
echo ===================================================
echo.
echo Services:
echo   - Streamlit Web UI: http://localhost:8501
echo   - FastAPI Backend:  http://localhost:8000
echo   - Health Endpoint:  http://localhost:8000/health
echo   - OpenAPI Docs:     http://localhost:8000/docs
echo.
echo Useful commands:
echo   - View live logs:     scripts\docker_logs.bat
echo   - Run smoke tests:    scripts\docker_test.bat
echo   - Stop containers:    scripts\docker_stop.bat
echo ===================================================
echo.
goto :EOF

:ERROR_EXIT
echo.
echo Startup failed. Please address the errors above.
pause
exit /b 1
