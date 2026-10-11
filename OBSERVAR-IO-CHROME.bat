@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Necessario Python com comando py.
  pause
  exit /b 1
)
py -3 -c "from PIL import ImageGrab" >nul 2>&1
if errorlevel 1 (
  echo Instalando dependencia de captura local (Pillow)...
  py -3 -m pip install -r requirements-desktop.txt
  if errorlevel 1 (
    echo Falha ao instalar Pillow.
    pause
    exit /b 1
  )
)
echo Abra sua conta no Chrome normal. Nao use a janela Chromium do Playwright.
py -3 -m app.browser_probe --game io --mode desktop --open-browser --seconds 60 --interval 10
pause
