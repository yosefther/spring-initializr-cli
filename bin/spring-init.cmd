@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%PROJECT_ROOT%\main.py" %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%PROJECT_ROOT%\main.py" %*
  exit /b %ERRORLEVEL%
)

echo Error: Python was not found. Install Python 3.12+ and ensure it is on PATH.
exit /b 1
