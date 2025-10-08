@echo off
REM Windows batch script to run the Streamlit metrics_app
REM This script is idempotent and can be run multiple times safely

echo ========================================
echo Metrics App Launcher
echo ========================================
echo.

REM Step 1: Check if Python is installed
echo [1/5] Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo Python found:
python --version
echo.

REM Step 2: Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo [2/5] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo [2/5] Virtual environment already exists.
)
echo.

REM Step 3: Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    echo.
    pause
    exit /b 1
)
echo Virtual environment activated.
echo.

REM Step 4: Upgrade pip and install dependencies
echo [4/5] Upgrading pip and installing dependencies...
echo This may take a moment on first run...
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo WARNING: Failed to upgrade pip, continuing anyway...
)

python -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies from requirements.txt.
    echo Please check that requirements.txt exists and is valid.
    echo.
    pause
    exit /b 1
)
echo Dependencies installed successfully.
echo.

REM Step 5: Run Streamlit app
echo [5/5] Starting Streamlit app...
echo.
echo ========================================
echo App is running! Press Ctrl+C to stop.
echo ========================================
echo.

python -m streamlit run app.py

REM After app stops
echo.
echo ========================================
echo App has stopped.
echo ========================================
echo.
pause
