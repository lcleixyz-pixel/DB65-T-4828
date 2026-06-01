@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "REQ_FILE=requirements.txt"
set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQ_STAMP=%VENV_DIR%\.requirements.installed.txt"

echo ========================================
echo   UV-Vis Tool - Setup Dependencies
echo ========================================
echo.

echo [1/3] Checking key files...
if not exist "%REQ_FILE%" (
    echo [ERROR] requirements.txt not found in: %cd%
    goto :fail
)
echo requirements.txt - OK

echo.
echo [2/3] Preparing Python virtual environment...
call :ensure_python_runtime
if errorlevel 1 goto :fail

echo.
echo [3/3] Installing dependencies...
call :install_dependencies
if errorlevel 1 goto :fail

echo.
echo ========================================
echo [OK] Setup complete.
echo.
echo Next step:
echo   Double-click "启动应用.bat" to run the app.
echo ========================================
echo.
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
    echo [TIP] Install Python, then run this script again.
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

:install_dependencies
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
exit /b 0

:fail
echo.
echo [FAIL] Setup did not complete.
pause
exit /b 1
