@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: AUTOSAR HLD Intelligence & Traceability Assistant - Windows Stopper
:: ============================================================================
:: Safely terminates FastAPI (port 8000) and Streamlit (port 8501) processes
:: started by the launcher without killing unrelated Python processes.
:: ============================================================================

echo.
echo =========================================
echo Stopping AUTOSAR HLD Assistant Services
echo =========================================
echo.

set "STOPPED_COUNT=0"

:: ----------------------------------------------------------------------------
:: 1. Check & Terminate FastAPI Process (Port 8000)
:: ----------------------------------------------------------------------------
for /f "tokens=5" %%A in ('netstat -ano ^| findstr LISTENING ^| findstr :8000') do (
    echo Stopping FastAPI process PID %%A on port 8000...
    taskkill /F /PID %%A >nul 2>&1
    if !errorlevel! equ 0 (
        echo [SUCCESS] Terminated FastAPI process PID %%A.
        set /a STOPPED_COUNT+=1
    ) else (
        echo [WARNING] Could not terminate process PID %%A.
    )
)

:: ----------------------------------------------------------------------------
:: 2. Check & Terminate Streamlit Process (Port 8501)
:: ----------------------------------------------------------------------------
for /f "tokens=5" %%A in ('netstat -ano ^| findstr LISTENING ^| findstr :8501') do (
    echo Stopping Streamlit process PID %%A on port 8501...
    taskkill /F /PID %%A >nul 2>&1
    if !errorlevel! equ 0 (
        echo [SUCCESS] Terminated Streamlit process PID %%A.
        set /a STOPPED_COUNT+=1
    ) else (
        echo [WARNING] Could not terminate process PID %%A.
    )
)

:: ----------------------------------------------------------------------------
:: 3. Summary of Stopped Services
:: ----------------------------------------------------------------------------
if !STOPPED_COUNT! GTR 0 (
    echo.
    echo =========================================
    echo [SUCCESS] AUTOSAR HLD Assistant services stopped successfully.
    echo Total processes terminated: !STOPPED_COUNT!
    echo =========================================
) else (
    echo.
    echo =========================================
    echo [INFO] No active processes found on ports 8000 or 8501.
    echo =========================================
)

echo.
pause
