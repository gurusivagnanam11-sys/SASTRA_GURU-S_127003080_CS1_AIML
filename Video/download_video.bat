
@echo off
setlocal

set "FILE_ID=1Fp9yBy_ukTX9h2evpwDOMVOZXDPxB1YN"
set "DEST=%~dp0Video"
set "OUTPUT=%DEST%\Video_Project_Original.mp4"

if not exist "%DEST%" mkdir "%DEST%"

echo Downloading original demonstration video from Google Drive...
echo.

where curl >nul 2>&1
if errorlevel 1 (
    echo ERROR: curl is not installed or not available in PATH.
    pause
    exit /b 1
)

curl -fL --retry 3 ^
  "https://drive.google.com/uc?export=download&id=%FILE_ID%" ^
  -o "%OUTPUT%"

if errorlevel 1 (
    echo.
    echo Download failed. Check the Google Drive sharing permissions.
    del "%OUTPUT%" 2>nul
    pause
    exit /b 1
)

echo.
echo Download request completed.
echo Check that the downloaded MP4 plays correctly:
echo "%OUTPUT%"
pause
