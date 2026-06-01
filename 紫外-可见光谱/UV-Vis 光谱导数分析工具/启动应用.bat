@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "APP_FILE=app.py"
set "REQ_FILE=requirements.txt"
set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQ_STAMP=%VENV_DIR%\.requirements.installed.txt"

echo ========================================
echo   UV-Vis Spectrum Derivative Tool
echo   Working dir: %cd%
echo ========================================
echo.

echo [1/4] Checking key files...
if not exist "%APP_FILE%" (
    echo [ERROR] app.py not found in: %cd%
    goto :fail
)
if not exist "%REQ_FILE%" (
    echo [ERROR] requirements.txt not found in: %cd%
    goto :fail
)
echo app.py           - OK
echo requirements.txt - OK

echo.
echo [2/4] Checking Python runtime...
call :ensure_python_runtime
if errorlevel 1 goto :fail

echo.
echo [3/4] Checking dependencies...
call :ensure_dependencies
if errorlevel 1 goto :fail

echo.
echo [4/4] Starting app...
echo ----------------------------------------
echo If browser is not opened automatically:
echo   http://localhost:8501
echo Close this window to stop the app.
echo ----------------------------------------
echo.
start "" "http://localhost:8501" >nul 2>&1
"%VENV_PY%" -m streamlit run "%APP_FILE%" --server.port 8501
if errorlevel 1 (
    echo.
    echo [ERROR] App exited with an error.
    goto :fail
)

echo.
echo [INFO] App has stopped.
pause
exit /b 0

:ensure_python_runtime
if exist "%VENV_PY%" (
    echo [INFO] Found existing virtual environment: %VENV_DIR%
    "%VENV_PY%" --version >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Existing .venv is invalid ^(usually copied from another computer^).
        call :recreate_venv
        exit /b %errorlevel%
    )
    "%VENV_PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Existing .venv is not using Python 3.8+.
        call :recreate_venv
        exit /b %errorlevel%
    )
    echo [OK] Using existing virtual environment: %VENV_DIR%
    "%VENV_PY%" --version
    exit /b 0
)
call :recreate_venv
exit /b %errorlevel%

:resolve_base_python
set "BASE_PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "BASE_PY=py -3"
if not defined BASE_PY (
    python --version >nul 2>&1
    if not errorlevel 1 set "BASE_PY=python"
)
if not defined BASE_PY (
    python3 --version >nul 2>&1
    if not errorlevel 1 set "BASE_PY=python3"
)

if not defined BASE_PY (
    echo [ERROR] Python 3.8+ not found on this computer.
    if exist "..\python\python-manager-25.2.msix" (
        echo [TIP] Found installer:
        echo       ..\python\python-manager-25.2.msix
    )
    echo [TIP] Install Python, then rerun this script.
    echo [TIP] Download page:
    echo       https://www.python.org/downloads/windows/
    exit /b 1
)

%BASE_PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Detected Python version is lower than 3.8.
    echo [TIP] Please install Python 3.8 or newer.
    exit /b 1
)
exit /b 0

:recreate_venv
call :resolve_base_python
if errorlevel 1 exit /b 1

if exist "%VENV_DIR%" (
    echo [INFO] Removing broken virtual environment...
    rmdir /s /q "%VENV_DIR%" >nul 2>&1
)
if exist "%VENV_DIR%" (
    echo [ERROR] Failed to remove %VENV_DIR%.
    echo [TIP] Close terminals/editors using this folder, then delete .venv manually.
    exit /b 1
)

echo [INFO] Creating virtual environment: %VENV_DIR%
%BASE_PY% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    exit /b 1
)

if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment created but python.exe was not found.
    exit /b 1
)

echo [OK] Created virtual environment.
"%VENV_PY%" --version
exit /b 0

:ensure_dependencies
set "NEED_INSTALL="
if not exist "%REQ_STAMP%" set "NEED_INSTALL=1"
if not defined NEED_INSTALL (
    fc /b "%REQ_FILE%" "%REQ_STAMP%" >nul 2>&1
    if errorlevel 1 set "NEED_INSTALL=1"
)
if not defined NEED_INSTALL (
    "%VENV_PY%" -c "import importlib.util,sys;mods=['streamlit','plotly','pandas','numpy','scipy','openpyxl','xlsxwriter','kaleido','streamlit_plotly_events','chardet'];missing=[m for m in mods if importlib.util.find_spec(m) is None];print('all-present' if not missing else 'missing=' + ','.join(missing));sys.exit(1 if missing else 0)"
    if errorlevel 1 set "NEED_INSTALL=1"
)

if defined NEED_INSTALL (
    echo [INFO] Installing dependencies. This may take a few minutes...
    "%VENV_PY%" -m pip install --upgrade pip
    if errorlevel 1 (
        echo [WARN] pip upgrade failed. Continue with current pip.
    )

    "%VENV_PY%" -m pip install -r "%REQ_FILE%"
    if errorlevel 1 (
        echo [WARN] Install from default index failed. Retry with Tsinghua mirror...
        "%VENV_PY%" -m pip install -r "%REQ_FILE%" -i https://pypi.tuna.tsinghua.edu.cn/simple
        if errorlevel 1 (
            echo [ERROR] Dependency installation failed.
            exit /b 1
        )
    )
    copy /y "%REQ_FILE%" "%REQ_STAMP%" >nul
    echo [OK] Dependencies installed.
) else (
    echo [OK] Dependencies are ready.
)
exit /b 0

:fail
echo.
echo [FAIL] Start-up was not completed.
pause
exit /b 1
