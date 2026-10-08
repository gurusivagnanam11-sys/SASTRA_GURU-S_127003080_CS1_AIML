@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: AUTOSAR HLD Intelligence & Traceability Assistant - Windows Launcher
:: ============================================================================
:: This script automatically:
:: 1. Resolves the project root directory dynamically.
:: 2. Verifies expected project file structure.
:: 3. Activates the Python virtual environment (.venv).
:: 4. Checks required dependencies (Python, Uvicorn, Ollama, qwen3:4b model).
:: 5. Checks if ports 8000 (FastAPI) and 8501 (Streamlit) are available.
:: 6. Launches FastAPI Backend and Streamlit UI in separate windows.
:: ============================================================================

echo.
echo =========================================
echo AUTOSAR HLD Assistant - Starting Launcher
echo =========================================
echo.

:: ----------------------------------------------------------------------------
:: 1. Detect Project Root Relative to Batch Script Location
:: ----------------------------------------------------------------------------
:: %~dp0 returns the drive and path of the directory containing this batch file.
:: %~dp0.. resolves to the parent directory (project root).
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

echo [INFO] Project Root detected at: "%PROJECT_ROOT%"

:: ----------------------------------------------------------------------------
:: 2. Check Expected Project Structure
:: ----------------------------------------------------------------------------
if not exist "%PROJECT_ROOT%\app\main.py" (
    echo [ERROR] Project file missing: app\main.py
    echo Please ensure the launcher script is inside the scripts\ folder of the project.
    goto :ERROR_EXIT
)

if not exist "%PROJECT_ROOT%\app\streamlit_app.py" (
    echo [ERROR] Project file missing: app\streamlit_app.py
    echo Please ensure the launcher script is inside the scripts\ folder of the project.
    goto :ERROR_EXIT
)

if not exist "%PROJECT_ROOT%\scripts\run_ui.py" (
    echo [ERROR] Project file missing: scripts\run_ui.py
    echo Please ensure the launcher script is inside the scripts\ folder of the project.
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 3. Detect and Activate Virtual Environment
:: ----------------------------------------------------------------------------
set "VENV_ACTIVATE="
if exist "%PROJECT_ROOT%\.venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=%PROJECT_ROOT%\.venv\Scripts\activate.bat"
) else if exist "%PROJECT_ROOT%\venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=%PROJECT_ROOT%\venv\Scripts\activate.bat"
)

if "%VENV_ACTIVATE%"=="" (
    echo ============================================================================
    echo [ERROR] Virtual environment not found!
    echo ============================================================================
    echo Expected virtual environment at .venv\Scripts\activate.bat
    echo.
    echo To create and set up the virtual environment, run the following commands:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    echo ============================================================================
    goto :ERROR_EXIT
)

echo [INFO] Activating virtual environment: "%VENV_ACTIVATE%"
call "%VENV_ACTIVATE%"

:: ----------------------------------------------------------------------------
:: 4. Check Python & Uvicorn Installation
:: ----------------------------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python executable not found after activating virtual environment.
    goto :ERROR_EXIT
)

python -m uvicorn --version >nul 2>&1
if errorlevel 1 (
    echo ============================================================================
    echo [ERROR] Uvicorn package is not installed in the virtual environment!
    echo ============================================================================
    echo Please install project dependencies using:
    echo   pip install -r requirements.txt
    echo ============================================================================
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 5. Check Ollama Service Installation
:: ----------------------------------------------------------------------------
ollama --version >nul 2>&1
if errorlevel 1 (
    echo ============================================================================
    echo [ERROR] Ollama is not installed or not in PATH!
    echo ============================================================================
    echo Ollama is required for local LLM inference.
    echo Please download and install Ollama from: https://ollama.com
    echo Ensure the 'ollama' executable is in your system PATH.
    echo ============================================================================
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 6. Check Ollama qwen3:4b Model Availability
:: ----------------------------------------------------------------------------
ollama list | findstr /I "qwen3:4b" >nul 2>&1
if errorlevel 1 (
    echo ============================================================================
    echo [ERROR] Ollama model 'qwen3:4b' is missing!
    echo ============================================================================
    echo The application requires the 'qwen3:4b' model for LLM provider operations.
    echo.
    echo Please pull the model manually by running:
    echo   ollama pull qwen3:4b
    echo ============================================================================
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 7. Check Port Availability (8000 and 8501)
:: ----------------------------------------------------------------------------
set "PORT_IN_USE="

for /f "tokens=5" %%A in ('netstat -ano ^| findstr LISTENING ^| findstr :8000') do (
    set "PORT_IN_USE=8000"
)
for /f "tokens=5" %%A in ('netstat -ano ^| findstr LISTENING ^| findstr :8501') do (
    set "PORT_IN_USE=8501"
)

if not "!PORT_IN_USE!"=="" (
    echo ============================================================================
    echo [ERROR] Port !PORT_IN_USE! is already in use!
    echo ============================================================================
    echo Either FastAPI ^(port 8000^) or Streamlit ^(port 8501^) is currently running.
    echo Please stop existing services before starting.
    echo You can stop existing project processes using:
    echo   scripts\stop_project.bat
    echo ============================================================================
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 8. Display Startup Summary
:: ----------------------------------------------------------------------------
echo =========================================
echo AUTOSAR HLD Intelligence Assistant
echo =========================================
echo FastAPI:   http://127.0.0.1:8000/docs
echo Streamlit: http://127.0.0.1:8501
echo Ollama:    qwen3:4b
echo =========================================
echo.
echo Launching services in separate processes...

:: ----------------------------------------------------------------------------
:: 9. Launch FastAPI Backend and Streamlit UI in Separate Windows
:: ----------------------------------------------------------------------------
start "AUTOSAR FastAPI Backend (http://127.0.0.1:8000/docs)" cmd /k "cd /d "%PROJECT_ROOT%" && call "%VENV_ACTIVATE%" && uvicorn app.main:app --host 127.0.0.1 --port 8000"

start "AUTOSAR Streamlit UI (http://127.0.0.1:8501)" cmd /k "cd /d "%PROJECT_ROOT%" && call "%VENV_ACTIVATE%" && python scripts/run_ui.py --port 8501"

echo [SUCCESS] Both FastAPI and Streamlit services have been started.
echo You can access:
echo   - FastAPI OpenAPI Docs: http://127.0.0.1:8000/docs
echo   - Streamlit Web UI:     http://127.0.0.1:8501
echo.
echo Keep the application windows open while using the assistant.
goto :EOF

:ERROR_EXIT
echo.
echo Launcher stopped due to an error.
pause
exit /b 1
