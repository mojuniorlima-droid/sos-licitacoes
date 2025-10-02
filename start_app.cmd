@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title PROGRAMA DE LICITAÇÃO - Start (SUPER)

rem ========= CONFIG BÁSICA =========
set "ROOT=%~dp0"
pushd "%ROOT%"
set "VENV_DIR=%ROOT%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "USE_REQUIREMENTS=1"    rem 1 = instala também o requirements.txt se existir
set "FALLBACK_MAIN=main.py" rem se não houver run_native.py, usa main.py

echo.
echo [0/7] Verificando Python instalado...

rem Tenta 3.13 -> 3.12 -> 3.11 -> python
set "PY_CMD="
for %%V in (3.13 3.12 3.11) do (
  py -%%V -c "print('ok')" 1>nul 2>nul && set "PY_CMD=py -%%V" && goto :got_py
)
python -c "print('ok')" 1>nul 2>nul && set "PY_CMD=python" && goto :got_py

echo [ERRO] Nao encontrei Python 3.11+.
echo Instale em https://www.python.org/downloads/ e rode de novo.
goto :end

:got_py
for /f "tokens=1-2*" %%A in ('%PY_CMD% -c "import sys;print(sys.version.split()[0])"') do set "PY_VER=%%A"
echo     Usando: %PY_CMD%  (Python %PY_VER%)

rem ========= 1/7: criar/usar venv =========
if not exist "%VENV_PY%" (
  echo.
  echo [1/7] Criando ambiente virtual (.venv)...
  %PY_CMD% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [ERRO] Falha ao criar a venv. Feche tudo e tente novamente.
    goto :end
  )
) else (
  echo.
  echo [1/7] Ambiente .venv detectado.
)

rem ========= 2/7: atualizar pip/setuptools/wheel =========
echo.
echo [2/7] Atualizando instalador (pip / wheel / setuptools)...
"%VENV_PY%" -m pip install --upgrade pip wheel setuptools

rem ========= 3/7: instalar do requirements.txt (opcional) =========
if "%USE_REQUIREMENTS%"=="1" if exist "%ROOT%requirements.txt" (
  echo.
  echo [3/7] Instalando dependencias do requirements.txt...
  "%VENV_PY%" -m pip install --no-cache-dir -r "%ROOT%requirements.txt"
) else (
  echo.
  echo [3/7] Pulando requirements.txt (nao encontrado ou desativado).
)

rem ========= 4/7: pacotes principais do projeto =========
echo.
echo [4/7] Instalando pacotes principais do projeto...
"%VENV_PY%" -m pip install --no-cache-dir ^
  flet==0.28.3 ^
  pypdf ^
  pillow ^
  openpyxl ^
  numpy ^
  scipy ^
  joblib ^
  threadpoolctl

rem ========= 5/7: scikit-learn (wheel binário) =========
echo.
echo [5/7] Instalando scikit-learn (binario)...
set "PIP_ONLY_BINARY=:all:"
"%VENV_PY%" -m pip install --no-cache-dir scikit-learn==1.7.2
set "PIP_ONLY_BINARY="

rem ========= 6/7: checagens rápidas / versoes =========
echo.
echo [6/7] Checando pacotes e versões...
"%VENV_PY%" - << PY
import sys
def safe(name, attr="__version__"):
    try:
        m=__import__(name)
        v=getattr(m, attr, None)
        print(f"{name:12s}", str(v) if v else "(sem __version__)")
    except Exception as e:
        print(f"{name:12s} ERRO ->", e)
print("Python      ", sys.version.split()[0], "->", sys.executable)
for mod in ["flet","pypdf","PIL","openpyxl","sklearn","numpy","scipy","joblib","threadpoolctl"]:
    safe(mod)
PY

rem ========= 7/7: iniciar app =========
echo.
echo [7/7] Iniciando o Programa de Licitacao...
set "TARGET=%ROOT%run_native.py"
if not exist "%TARGET%" set "TARGET=%ROOT%%FALLBACK_MAIN%"
if not exist "%TARGET%" (
  echo [ERRO] Nao encontrei run_native.py nem %FALLBACK_MAIN%.
  goto :end
)

"%VENV_PY%" "%TARGET%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo App finalizado.
) else (
  echo ⚠ O app encerrou com codigo %EXITCODE%.
)

:end
echo.
pause
endlocal
