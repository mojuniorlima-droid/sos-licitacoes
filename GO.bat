@echo off
setlocal enableextensions
cd /d "%~dp0"

echo [1/3] Preparando ambiente (venv)...
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv || python -m venv .venv
)

echo [2/3] Ativando venv...
call ".venv\Scripts\activate.bat"

echo [3/3] Instalando dependencias (se necessario)...
if exist "requirements.txt" (
  pip install -r requirements.txt >nul
)

echo Iniciando no navegador...
python run_web.py
echo.
echo (Feche a janela pra encerrar. Pressione uma tecla para sair...)
pause >nul
