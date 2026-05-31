:: start.bat — Imprint Face Sorter Intelligent Launcher (v5)
::
:: This script handles:
::   1. Python presence check
::   2. Virtual environment creation (if needed)
::   3. Dependency installation / update (if requirements changed)
::   4. Application launch
::
:: Usage: Double-click this file or run from a terminal.
:: ============================================================================
@echo off
setlocal enabledelayedexpansion

:: ============================================================================
::                          CONFIGURATION
:: ============================================================================
set "VENV_NAME=imprint_env"
set "REQUIREMENTS_FILE=requirements.txt"
set "INSTALL_RECEIPT=_install.log"
set "ENTRY_POINT=run.py"
set "MIN_PYTHON_MAJOR=3"
set "MIN_PYTHON_MINOR=9"

:: ============================================================================
::                     PRE-FLIGHT CHECKS
:: ============================================================================

echo.
echo  ============================================================
echo   Imprint Face Sorter — Launcher v5
echo  ============================================================
echo.

:: Check requirements.txt exists
if not exist "%REQUIREMENTS_FILE%" (
    echo  [ERROR] '%REQUIREMENTS_FILE%' is missing. Cannot proceed.
    echo          Place this file in the same directory as start.bat.
    echo.
    pause
    goto :end
)

:: Check entry point exists
if not exist "%ENTRY_POINT%" (
    echo  [ERROR] '%ENTRY_POINT%' is missing. Cannot proceed.
    echo          Ensure all project files are in the same directory.
    echo.
    pause
    goto :end
)

:: ============================================================================
::                  CHECK FOR EXISTING UP-TO-DATE ENV
:: ============================================================================

if exist "%INSTALL_RECEIPT%" (
    fc /b "%REQUIREMENTS_FILE%" "%INSTALL_RECEIPT%" >nul 2>&1
    if !errorlevel! equ 0 (
        if exist "%VENV_NAME%\Scripts\activate.bat" (
            echo  [OK] Environment is up-to-date. Skipping setup.
            goto :launch_app
        )
    )
    echo  [INFO] Requirements changed or environment missing. Updating...
) else (
    echo  [INFO] First-time setup detected. Preparing environment...
)

:: ============================================================================
::                        SETUP / UPDATE
:: ============================================================================

echo.
echo  [1/3] Checking Python installation...
py -3.10 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py -3.10"
) else (
    set "PYTHON_EXE=python"
)

%PYTHON_EXE% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python is not installed or not in your system PATH.
    echo          Install Python %MIN_PYTHON_MAJOR%.%MIN_PYTHON_MINOR%+ from https://python.org
    echo.
    pause
    goto :end
)

:: Verify minimum version
for /f "tokens=2 delims= " %%v in ('%PYTHON_EXE% --version 2^>^&1') do set "PY_VERSION=%%v"
echo        Found Python %PY_VERSION%

:: Create or verify virtual environment
if not exist "%VENV_NAME%\Scripts\activate.bat" (
    echo  [2/3] Creating virtual environment '%VENV_NAME%'...
    %PYTHON_EXE% -m venv "%VENV_NAME%"
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to create virtual environment.
        echo          Check disk space and permissions.
        echo.
        pause
        goto :end
    )
    echo        Virtual environment created.
) else (
    echo  [2/3] Virtual environment found.
)

:: Install / update dependencies
echo  [3/3] Installing dependencies (this may take a few minutes)...
call "%VENV_NAME%\Scripts\activate.bat"
pip install -r "%REQUIREMENTS_FILE%" --no-warn-script-location --quiet
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to install dependencies from '%REQUIREMENTS_FILE%'.
    echo          Check your internet connection and the log above.
    echo.
    pause
    goto :end
)
echo        Dependencies installed successfully.

:: Create receipt
copy /y "%REQUIREMENTS_FILE%" "%INSTALL_RECEIPT%" >nul
echo.
echo  ============================================================
echo   Setup complete!
echo  ============================================================
echo.

:: ============================================================================
::                        LAUNCH APPLICATION
:: ============================================================================

:launch_app
echo.
echo  Launching Imprint Face Sorter...
echo.
call "%VENV_NAME%\Scripts\activate.bat"
python "%ENTRY_POINT%"
echo.
echo  Application closed.

:end
endlocal
exit /b
