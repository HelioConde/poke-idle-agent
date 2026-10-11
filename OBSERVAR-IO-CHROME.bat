@echo off
setlocal
cd /d "%~dp0"
if /I "%~1"=="--check" goto :self_test
if /I "%~1"=="--capturas" goto :capture_frames
echo MONITOR DE ABAS: detecta jogos mesmo em abas inativas.
echo Instale a extensao da pasta chrome_extension uma vez.
call INICIAR-MONITOR-ABAS.bat
exit /b %ERRORLEVEL%

:capture_frames
echo MODO LEGADO DE IMAGENS: so encontra a ABA SELECIONADA na janela.
echo Para detectar abas inativas, feche e execute sem --capturas.
py -3 -c "from PIL import ImageGrab" >nul 2>&1
if errorlevel 1 goto :install_pillow
goto :run_frames

:install_pillow
py -3 -m pip install -r requirements-desktop.txt
if errorlevel 1 goto :install_failed

:run_frames
py -3 -m app.browser_probe --game io --mode window --seconds 60 --interval 10
set "EXIT_CODE=%ERRORLEVEL%"
pause
exit /b %EXIT_CODE%

:install_failed
echo Falha ao instalar Pillow.
pause
exit /b 1

:self_test
echo Launcher IO: sintaxe BAT OK
exit /b 0
