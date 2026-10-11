@echo off
if /I "%~1"=="--check" goto :self_test
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
exit /b %ERRORLEVEL%

:self_test
echo Teste do agente: sintaxe BAT OK
exit /b 0
