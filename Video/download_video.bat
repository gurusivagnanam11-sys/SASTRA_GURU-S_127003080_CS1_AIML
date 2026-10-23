```bat
@echo off
setlocal EnableExtensions

:: ============================================================
:: AUTOSAR HLD Assistant - Original Demo Video Downloader
:: Downloads the original uncompressed video from Google Drive
:: Skips downloading if the video already exists and is non-empty
:: ============================================================

set "FILE_ID=1Fp9yBy_ukTX9h2evpwDOMVOZXDPxB1YN"
set "DEST=%~dp0Video"
set "OUTPUT=%DEST%\AUTOSAR_HLD_Original_Uncompressed.mp4"
set "TEMP_FILE=%DEST%\AUTOSAR_HLD_Original_Uncompressed.download"

echo.
echo ============================================
echo AUTOSAR HLD - Original Video Downloader
echo ============================================
echo.

:: Create Video folder if needed
if not exist "%DEST%" (
    mkdir "%DEST%"
    if errorlevel 1 (
        echo [ERROR] Could not create Video folder.
        pause
        exit /b 1
    )
)

:: Skip if the video already exists and is non-empty
if exist "%OUTPUT%" (
    for %%F in ("%OUTPUT%") do if %%~zF GTR 0 (
        echo [INFO] Original video already exists.
        echo [INFO] Skipping download.
        echo [INFO] File: "%OUTPUT%"
        goto :DONE
    )
)

:: Check curl
where curl >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl is not installed or not available in PATH.
    pause
    exit /b 1
)

echo [INFO] Downloading original video from Google Drive...
echo [INFO] Destination: "%OUTPUT%"
echo.

del "%TEMP_FILE%" 2>nul

curl -fL --retry 3 --connect-timeout 20 ^
  "https://drive.google.com/uc?export=download&id=%FILE_ID%" ^
  -o "%TEMP_FILE%"

if errorlevel 1 (
    echo.
    echo [ERROR] Download failed.
    echo Check your internet connection and Google Drive sharing permissions.
    del "%TEMP_FILE%" 2>nul
    pause
    exit /b 1
)

:: Validate that the response appears to be an MP4 file
set "CHECK_FILE=%TEMP_FILE%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p=$env:CHECK_FILE; if (!(Test-Path -LiteralPath $p)) { exit 1 }; $s=[IO.File]::OpenRead($p); try { if ($s.Length -lt 12) { exit 1 }; $s.Position=4; $b=[char[]]@($s.ReadByte(),$s.ReadByte(),$s.ReadByte(),$s.ReadByte()); if (-join $b -eq 'ftyp') { exit 0 } else { exit 1 } } finally { $s.Dispose() }"

if errorlevel 1 (
    echo.
    echo [ERROR] Google Drive did not return a valid MP4 file.
    echo It may require a download confirmation or different sharing permissions.
    echo The invalid download will be deleted.
    del "%TEMP_FILE%" 2>nul
    pause
    exit /b 1
)

move /Y "%TEMP_FILE%" "%OUTPUT%" >nul
if errorlevel 1 (
    echo [ERROR] Could not save the downloaded video.
    del "%TEMP_FILE%" 2>nul
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Original video downloaded successfully.
echo [INFO] Saved as:
echo "%OUTPUT%"

:DONE
echo.
echo Finished.
pause
exit /b 0
```
