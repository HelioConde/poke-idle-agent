@echo off
if /I "%~1"=="--check" goto :self_test
cd /d "%~dp0"
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  py -3 dashboard.py
) else (
  python dashboard.py
)
if errorlevel 1 pause
exit /b %ERRORLEVEL%

:self_test
echo Painel local: sintaxe BAT OK
exit /b 0
