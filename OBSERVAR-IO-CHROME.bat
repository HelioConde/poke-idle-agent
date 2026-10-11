@echo off
setlocal
cd /d "%~dp0"
if /I "%~1"=="--check" goto :self_test
where py >nul 2>&1
if errorlevel 1 goto :python_missing
py -3 -c "from PIL import ImageGrab" >nul 2>&1
if errorlevel 1 goto :install_pillow
goto :capture

:install_pillow
echo Instalando dependencia local de captura - Pillow...
py -3 -m pip install -r requirements-desktop.txt
if errorlevel 1 goto :install_failed

:capture
echo Use seu Chrome normal para entrar no jogo.
echo Este programa nao controla o login nem le senhas.
py -3 -m app.browser_probe --game io --mode desktop --open-browser --seconds 60 --interval 10
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" echo Captura encerrada com erro %EXIT_CODE%.
pause
exit /b %EXIT_CODE%

:install_failed
echo Falha ao instalar Pillow.
pause
exit /b 1

:python_missing
echo Comando py nao encontrado. Instale Python 3.11 ou superior.
pause
exit /b 1

:self_test
echo Verificacao basica do arquivo BAT: OK
exit /b 0
