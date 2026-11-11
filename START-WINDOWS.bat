@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 app.py --open
) else (
  python app.py --open
)
pause
