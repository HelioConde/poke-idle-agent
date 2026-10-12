@echo off
setlocal
cd /d "%~dp0"
if /I "%~1"=="--check" goto :self_test
if /I "%~1"=="--test" goto :tests
echo ===========================================
echo         IDLE GAME AGENT - INICIAR TUDO
echo ===========================================
echo Um painel, IO monitor e ferramentas World.
echo IO: somente leitura e automacoes ja aprovadas por acao.
echo World: somente analise manual, sem bot externo.
echo.
where py >nul 2>&1
if errorlevel 1 goto :python_fallback
py -3 -m app.unified_launcher
set "EXIT_CODE=%ERRORLEVEL%"
goto :finish

:python_fallback
where python >nul 2>&1
if errorlevel 1 goto :missing_python
python -m app.unified_launcher
set "EXIT_CODE=%ERRORLEVEL%"
goto :finish

:missing_python
echo [ERRO] Instale Python 3.11+ e marque a opcao Add Python to PATH.
set "EXIT_CODE=1"
goto :finish

:tests
where py >nul 2>&1
if errorlevel 1 goto :python_tests
py -3 -m unittest discover -s tests -v
exit /b %ERRORLEVEL%

:python_tests
python -m unittest discover -s tests -v
exit /b %ERRORLEVEL%

:self_test
if not exist "app\unified_launcher.py" exit /b 2
if not exist "dashboard.py" exit /b 2
echo INICIAR-TUDO: sintaxe e arquivos OK
exit /b 0

:finish
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
