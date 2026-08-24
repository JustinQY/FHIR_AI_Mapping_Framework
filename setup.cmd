@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    exit /b 1
)

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt was not found in %CD%.
    exit /b 1
)

echo [SETUP] Installing project dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [OK] Project dependencies are installed.
echo Run: python main.py