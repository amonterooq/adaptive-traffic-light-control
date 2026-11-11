@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Preparando el entorno por primera vez...
  py -3.12 -m venv .venv
  if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, traci" >nul 2>&1
if errorlevel 1 (
  echo Instalando dependencias. La primera vez necesita Internet.
  ".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
  if errorlevel 1 goto error
)
".venv\Scripts\python.exe" programa\abrir.py %*
if errorlevel 1 goto error
exit /b 0
:error
echo No se pudo iniciar. Comprueba que Python 3.12 esta instalado y revisa el mensaje anterior.
pause
exit /b 1
