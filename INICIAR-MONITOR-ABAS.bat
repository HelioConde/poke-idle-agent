@echo off
setlocal
cd /d "%~dp0"
if /I "%~1"=="--check" goto :self_test
where py >nul 2>&1
if errorlevel 1 goto :missing_python
echo Localizando abas do Chrome sem trocar nem clicar nas abas...
echo Acesse http://127.0.0.1:8768 e configure a extensao da pasta chrome_extension.
py -3 -m app.tab_registry --port 8768
pause
exit /b %ERRORLEVEL%

:missing_python
echo Python com comando py nao encontrado.
pause
exit /b 1

:self_test
echo Monitor de abas: sintaxe BAT OK
exit /b 0
