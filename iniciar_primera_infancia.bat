@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

title Primera Infancia - Lanzador local estable Python 3.13

echo ============================================================
echo   PRIMERA INFANCIA - INICIO LOCAL BACKEND + FRONTEND
echo ============================================================
echo.
echo Este inicio reutiliza el entorno virtual existente.
echo NO ejecuta pip ni reinstala dependencias en cada arranque.
echo.

REM Puede ejecutarse desde la raiz o desde SCRIPTS_WINDOWS_PRIMERA_INFANCIA.
set "ROOT=%~dp0"
if not exist "%ROOT%backend\" if exist "%~dp0..\backend\" set "ROOT=%~dp0..\"
for %%I in ("%ROOT%.") do set "ROOT=%%~fI\"

set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "RUN_DIR=%ROOT%deploy"
set "BACKEND_PORT=5000"
set "FRONT_PORT="
set "VENV_PY=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "PREP_LAUNCHER=%ROOT%PREPARAR_ENTORNO_PYTHON_313.bat"
set "ENV_CHECK_LOG=%RUN_DIR%\verificacion_entorno_python.log"

if not exist "%RUN_DIR%" mkdir "%RUN_DIR%" >nul 2>&1

if not exist "%BACKEND_DIR%\" (
  echo [ERROR] No se encontro la carpeta backend en:
  echo %BACKEND_DIR%
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\" (
  echo [ERROR] No se encontro la carpeta frontend en:
  echo %FRONTEND_DIR%
  pause
  exit /b 1
)

echo Proyecto detectado en:
echo %ROOT%
echo.

echo [1/8] Validando el entorno virtual existente...
set "ENTORNO_OK=0"
if exist "%VENV_PY%" (
  "%VENV_PY%" -c "import pandas, flask, PIL, openpyxl, flask_cors, flask_jwt_extended, flask_sqlalchemy; print('ENTORNO_OK')" > "%ENV_CHECK_LOG%" 2>&1
  if not errorlevel 1 set "ENTORNO_OK=1"
)

if "%ENTORNO_OK%"=="0" (
  echo.
  echo [AVISO] El entorno Python no existe o esta incompleto.
  echo El inicio normal NO intentara instalar paquetes sobre un entorno en uso.
  if exist "%ENV_CHECK_LOG%" (
    echo.
    echo Ultimo diagnostico:
    type "%ENV_CHECK_LOG%"
  )
  echo.
  if not exist "%PREP_LAUNCHER%" (
    echo [ERROR] No se encontro:
    echo %PREP_LAUNCHER%
    pause
    exit /b 1
  )
  choice /C SN /N /M "Deseas preparar o reparar ahora el entorno Python 3.13? [S/N]: "
  if errorlevel 2 (
    echo Operacion cancelada. Ejecuta PREPARAR_ENTORNO_PYTHON_313.bat cuando estes listo.
    pause
    exit /b 1
  )
  call "%PREP_LAUNCHER%"
  if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo preparar el entorno Python.
    pause
    exit /b 1
  )
  "%VENV_PY%" -c "import pandas, flask, PIL, openpyxl, flask_cors, flask_jwt_extended, flask_sqlalchemy; print('ENTORNO_OK')" > "%ENV_CHECK_LOG%" 2>&1
  if errorlevel 1 (
    echo [ERROR] La preparacion termino, pero el entorno sigue incompleto.
    type "%ENV_CHECK_LOG%"
    pause
    exit /b 1
  )
)

for /f "tokens=2" %%V in ('"%VENV_PY%" --version 2^>^&1') do set "VENV_VERSION=%%V"
echo [OK] Entorno virtual listo: Python !VENV_VERSION!

echo [2/8] Dependencias verificadas. No se ejecutara pip en este inicio.

if not exist "%BACKEND_DIR%\archivos_actualizados" mkdir "%BACKEND_DIR%\archivos_actualizados"
if not exist "%BACKEND_DIR%\uploads" mkdir "%BACKEND_DIR%\uploads"
if not exist "%BACKEND_DIR%\logs" mkdir "%BACKEND_DIR%\logs"
if not exist "%BACKEND_DIR%\backups" mkdir "%BACKEND_DIR%\backups"
echo [3/8] Carpetas de trabajo verificadas.

echo.
echo [4/8] Verificando puerto del backend %BACKEND_PORT%...
set "BACKEND_BUSY=0"
for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%BACKEND_PORT% .*LISTENING"') do (
  set "BACKEND_BUSY=1"
  set "BACKEND_PID=%%A"
)

if "%BACKEND_BUSY%"=="1" (
  echo [AVISO] El puerto %BACKEND_PORT% ya esta ocupado por el PID !BACKEND_PID!.
  choice /C SN /N /M "Deseas cerrar ese proceso para iniciar este backend? [S/N]: "
  if errorlevel 2 (
    echo Operacion cancelada. Cierra manualmente el proceso y vuelve a intentar.
    pause
    exit /b 1
  )
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%BACKEND_PORT% .*LISTENING"') do (
    echo Cerrando PID %%A en puerto %BACKEND_PORT%...
    taskkill /PID %%A /F >nul 2>&1
  )
  timeout /t 2 /nobreak >nul
)

echo.
echo [5/8] Buscando puerto libre para frontend...
for %%P in (8080 8081 8090 9000 5500 5173) do (
  netstat -ano | findstr /R /C:":%%P .*LISTENING" >nul
  if errorlevel 1 (
    if not defined FRONT_PORT set "FRONT_PORT=%%P"
  )
)

if not defined FRONT_PORT (
  echo [ERROR] No encontre puerto libre para frontend.
  pause
  exit /b 1
)

echo Frontend usara puerto: %FRONT_PORT%
set "FRONTEND_URL=http://127.0.0.1:%FRONT_PORT%"
set "BACKEND_URL=http://127.0.0.1:%BACKEND_PORT%"
set "LOCAL_ALLOWED_ORIGINS=http://127.0.0.1:%FRONT_PORT%,http://localhost:%FRONT_PORT%,http://127.0.0.1:8080,http://localhost:8080,http://127.0.0.1:8081,http://localhost:8081,http://127.0.0.1:8090,http://localhost:8090,http://127.0.0.1:9000,http://localhost:9000,http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:5173,http://localhost:5173"

echo [6/8] Preparando configuracion local temporal...
set "RUN_BACKEND_CMD=%RUN_DIR%\_run_backend_local.cmd"
set "RUN_FRONTEND_CMD=%RUN_DIR%\_run_frontend_local.cmd"

(
  echo @echo off
  echo chcp 65001 ^>nul
  echo title Primera Infancia - Backend Flask
  echo cd /d "%BACKEND_DIR%"
  echo set "APP_ENV=development"
  echo set "FLASK_ENV=development"
  echo set "SERVER_MODE=LOCAL"
  echo set "FLASK_HOST=127.0.0.1"
  echo set "FLASK_PORT=%BACKEND_PORT%"
  echo set "PORT=%BACKEND_PORT%"
  echo set "LIAM_AVATAR_3D_ENABLED=true"
  echo set "FRONTEND_PORT=%FRONT_PORT%"
  echo set "FRONTEND_ORIGIN=%FRONTEND_URL%"
  echo set "ALLOWED_ORIGINS=%LOCAL_ALLOWED_ORIGINS%"
  echo set "BACKEND_URL=%BACKEND_URL%"
  echo set "DATABASE_PATH=database.sqlite3"
  echo set "DATABASE_URL=sqlite:///database.sqlite3"
  echo set "UPLOAD_FOLDER=uploads"
  echo set "OUTPUT_FOLDER=archivos_actualizados"
  echo set "TEMPLATES_FOLDER=templates_originales"
  echo set "LOG_FOLDER=logs"
  echo set "BACKUPS_FOLDER=backups"
  echo set "SESSION_COOKIE_SECURE=false"
  echo set "SESSION_COOKIE_SAMESITE=Lax"
  echo set "FORCE_HTTPS=false"
  echo set "PYTHONUTF8=1"
  echo set "PYTHONIOENCODING=utf-8"
  echo echo Backend local: %BACKEND_URL%
  echo echo Frontend permitido: %FRONTEND_URL%
  echo "%VENV_PY%" app.py
) > "%RUN_BACKEND_CMD%"

(
  echo @echo off
  echo chcp 65001 ^>nul
  echo title Primera Infancia - Frontend local
  echo cd /d "%FRONTEND_DIR%"
  echo echo Frontend local: %FRONTEND_URL%
  echo echo Backend configurado: %BACKEND_URL%
  echo "%VENV_PY%" -m http.server %FRONT_PORT% --bind 127.0.0.1
) > "%RUN_FRONTEND_CMD%"

echo [7/8] Iniciando backend Flask...
start "Primera Infancia - Backend Flask" cmd /k ""%RUN_BACKEND_CMD%""
timeout /t 5 /nobreak >nul

echo [8/8] Iniciando frontend local...
start "Primera Infancia - Frontend" cmd /k ""%RUN_FRONTEND_CMD%""
timeout /t 2 /nobreak >nul
start "" "%FRONTEND_URL%"

echo ============================================================
echo Plataforma iniciada sin reinstalar dependencias.
echo Backend:  %BACKEND_URL%
echo Frontend: %FRONTEND_URL%
echo.
echo Para el tunel, deja estas ventanas abiertas y ejecuta:
echo 02_INICIAR_CLOUDFLARE_DOBLE_CLIC.bat
echo ============================================================
echo.
pause
endlocal
