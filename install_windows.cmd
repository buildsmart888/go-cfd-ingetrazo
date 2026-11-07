@echo off
setlocal EnableExtensions
set "SRC=%~dp0go_cfd"
set "DEST=%APPDATA%\ingetrazo\plugins\go_cfd"
set "BK=%LOCALAPPDATA%\GOEngineering\PluginBackups"
if not exist "%SRC%\__init__.py" (
  echo ERROR: go_cfd package must be alongside this installer.
  exit /b 1
)
if exist "%DEST%" (
  if not exist "%BK%" mkdir "%BK%"
  if errorlevel 1 exit /b 1
  set "STAMP=%RANDOM%%RANDOM%"
  xcopy "%DEST%" "%BK%\go_cfd_%STAMP%\" /E /I /Q /Y >nul
  if errorlevel 1 exit /b 1
  rmdir /S /Q "%DEST%"
  if errorlevel 1 exit /b 1
)
if not exist "%DEST%" mkdir "%DEST%"
if errorlevel 1 exit /b 1
xcopy "%SRC%" "%DEST%\" /E /I /Q /Y >nul
if errorlevel 1 exit /b 1
echo Installed to %DEST%
echo Restart IngeTrazo and open Extensions - GO CFD.
pause
exit /b 0
