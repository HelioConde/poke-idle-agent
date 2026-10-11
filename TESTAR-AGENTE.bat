@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  py -3 -m unittest discover -s tests -v
  py -3 -m app.agent --steps 15
) else (
  python -m unittest discover -s tests -v
  python -m app.agent --steps 15
)
pause
