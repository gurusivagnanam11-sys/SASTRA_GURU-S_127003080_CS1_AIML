
@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ============================================================================
:: AUTOSAR HLD Intelligence & Traceability Assistant - Windows Launcher
:: ============================================================================

echo.
echo =========================================
echo AUTOSAR HLD Assistant - Starting Launcher
echo =========================================
echo.

:: ----------------------------------------------------------------------------
:: 1. Detect Project Root
:: ----------------------------------------------------------------------------
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

echo [INFO] Project Root: "%PROJECT_ROOT%"

:: ----------------------------------------------------------------------------
:: 2. Check Expected Project Structure
:: ----------------------------------------------------------------------------
if not exist "%PROJECT_ROOT%\app\main.py" (
    echo [ERROR] Missing app\main.py
    echo Ensure this launcher is inside the project's scripts folder.
    goto :ERROR_EXIT
)

if not exist "%PROJECT_ROOT%\app\streamlit_app.py" (
    echo [ERROR] Missing app\streamlit_app.py
    goto :ERROR_EXIT
)

if not exist "%PROJECT_ROOT%\scripts\run_ui.py" (
    echo [ERROR] Missing scripts\run_ui.py
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 3. Download Original Uncompressed Demo Video If Needed
:: ----------------------------------------------------------------------------
set "VIDEO_DIR=%PROJECT_ROOT%\Video"
set "VIDEO_FILE=%VIDEO_DIR%\AUTOSAR_HLD_Original_Uncompressed.mp4"
set "VIDEO_ID=1Fp9yBy_ukTX9h2evpwDOMVOZXDPxB1YN"
set "VIDEO_URL=https://drive.google.com/uc?export=download&id=%VIDEO_ID%"

if not exist "%VIDEO_DIR%" (
    mkdir "%VIDEO_DIR%"
    if errorlevel 1 (
        echo [ERROR] Could not create the Video folder.
        goto :ERROR_EXIT
    )
)

if exist "%VIDEO_FILE%" (
    for %%F in ("%VIDEO_FILE%") do set "VIDEO_SIZE=%%~zF"
    if !VIDEO_SIZE! GTR 0 (
        echo [INFO] Original video already exists. Skipping download.
        echo [INFO] File: "%VIDEO_FILE%"
        goto :VIDEO_DOWNLOAD_DONE
    )
)

echo.
echo =========================================
echo Checking Original Demo Video
echo =========================================
echo [INFO] Downloading original video from Google Drive...

where curl >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl was not found. Install or enable curl, then retry.
    goto :ERROR_EXIT
)

set "TEMP_VIDEO=%VIDEO_DIR%\AUTOSAR_HLD_Original_Uncompressed.download"

del "%TEMP_VIDEO%" 2>nul

curl -fL --retry 2 --connect-timeout 20 ^
    "%VIDEO_URL%" ^
    -o "%TEMP_VIDEO%"

if errorlevel 1 (
    echo [ERROR] Video download failed.
    echo Check that the Google Drive file is accessible to anyone with the link.
    del "%TEMP_VIDEO%" 2>nul
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: Validate MP4 signature.
:: MP4 files normally contain "ftyp" at byte offset 4.
:: This prevents saving a typical Google Drive HTML page as an MP4.
:: ----------------------------------------------------------------------------
set "TEMP_VIDEO_CHECK=%TEMP_VIDEO%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p=$env:TEMP_VIDEO_CHECK; if (!(Test-Path -LiteralPath $p)) { exit 1 }; $s=[IO.File]::OpenRead($p); try { if ($s.Length -lt 12) { exit 1 }; $s.Position=4; $b1=$s.ReadByte(); $b2=$s.ReadByte(); $b3=$s.ReadByte(); $b4=$s.ReadByte(); if ([char]$b1 -eq 'f' -and [char]$b2 -eq 't' -and [char]$b3 -eq 'y' -and [char]$b4 -eq 'p') { exit 0 } else { exit 1 } } finally { $s.Dispose() }"

if errorlevel 1 (
    echo.
    echo [ERROR] The downloaded file does not appear to be a valid MP4.
    echo Google Drive may require a download confirmation or access permission.
    echo No invalid video will be kept under the final filename.
    del "%TEMP_VIDEO%" 2>nul
    goto :ERROR_EXIT
)

move /Y "%TEMP_VIDEO%" "%VIDEO_FILE%" >nul
if errorlevel 1 (
    echo [ERROR] Could not move the video to its final location.
    del "%TEMP_VIDEO%" 2>nul
    goto :ERROR_EXIT
)

echo [SUCCESS] Original demo video downloaded and validated.
echo [INFO] Saved to: "%VIDEO_FILE%"

:VIDEO_DOWNLOAD_DONE

:: ----------------------------------------------------------------------------
:: 4. Detect and Activate Virtual Environment
:: ----------------------------------------------------------------------------
set "VENV_ACTIVATE="

if exist "%PROJECT_ROOT%\.venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=%PROJECT_ROOT%\.venv\Scripts\activate.bat"
) else if exist "%PROJECT_ROOT%\venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=%PROJECT_ROOT%\venv\Scripts\activate.bat"
)

if not defined VENV_ACTIVATE (
    echo.
    echo [ERROR] Virtual environment not found.
    echo Create it with:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    goto :ERROR_EXIT
)

echo [INFO] Activating virtual environment...
call "%VENV_ACTIVATE%"

:: ----------------------------------------------------------------------------
:: 5. Check Python and Uvicorn
:: ----------------------------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found after activating the environment.
    goto :ERROR_EXIT
)

python -m uvicorn --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Uvicorn is missing. Run:
    echo   pip install -r requirements.txt
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 6. Check Ollama
:: ----------------------------------------------------------------------------
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama is not installed or is not in PATH.
    echo Install it from https://ollama.com
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 7. Check Required Ollama Model
:: ----------------------------------------------------------------------------
ollama list | findstr /I "qwen2.5:3b" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama model qwen2.5:3b is missing.
    echo Run: ollama pull qwen2.5:3b
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 8. Check Ports 8000 and 8501
:: ----------------------------------------------------------------------------
set "PORT_IN_USE="

for /f "tokens=2,5" %%A in ('netstat -ano ^| findstr LISTENING ^| findstr /R /C:":8000 " /C:":8501 "') do (
    set "LOCAL_ENDPOINT=%%A"
    set "LOCAL_PORT="
    for /f "tokens=2 delims=:" %%P in ("!LOCAL_ENDPOINT!") do set "LOCAL_PORT=%%P"
    if "!LOCAL_PORT!"=="8000" set "PORT_IN_USE=8000"
    if "!LOCAL_PORT!"=="8501" set "PORT_IN_USE=8501"
)

if defined PORT_IN_USE (
    echo [ERROR] Port !PORT_IN_USE! is already in use.
    echo Stop the existing service before restarting the launcher.
    goto :ERROR_EXIT
)

:: ----------------------------------------------------------------------------
:: 9. Launch FastAPI and Streamlit
:: ----------------------------------------------------------------------------
echo.
echo =========================================
echo AUTOSAR HLD Intelligence Assistant
echo =========================================
echo FastAPI:   http://127.0.0.1:8000/docs
echo Streamlit: http://127.0.0.1:8501
echo Ollama:    qwen2.5:3b
echo Video:     "%VIDEO_FILE%"
echo =========================================
echo.
echo Launching services in separate windows...

start "AUTOSAR FastAPI Backend" cmd /k "cd /d ""%PROJECT_ROOT%"" && call ""%VENV_ACTIVATE%"" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

start "AUTOSAR Streamlit UI" cmd /k "cd /d ""%PROJECT_ROOT%"" && call ""%VENV_ACTIVATE%"" && python scripts/run_ui.py --port 8501"

echo.
echo [SUCCESS] Startup commands have been launched.
echo FastAPI docs: http://127.0.0.1:8000/docs
echo Streamlit UI: http://127.0.0.1:8501
echo Keep both service windows open while using the assistant.
goto :EOF

:ERROR_EXIT
echo.
echo Launcher stopped because an error occurred.
pause
exit /b 1

