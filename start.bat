@echo off
cd /d "%~dp0"
set "PATH=%APPDATA%\npm;%PATH%"
python scripts/startup.py %*
pause
