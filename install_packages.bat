@echo off

REM Set paths
set PROJECT_DIR=%~dp0
set VENV_NAME=pdf_merger_with_email
set VENV_DIR=%PROJECT_DIR%%VENV_NAME%
set REQUIREMENTS_FILE=%PROJECT_DIR%requirements.txt

REM Check if virtual environment exists, create if not
if not exist "%VENV_DIR%" (
    echo Creating virtual environment %VENV_NAME%...
    python -m venv "%VENV_DIR%"
    
    REM Activate virtual environment
    call "%VENV_DIR%\Scripts\activate"
    
    REM Install Python packages from requirements.txt
    pip install -r "%REQUIREMENTS_FILE%"
    
    REM Deactivate virtual environment
    deactivate
)

echo Virtual environment %VENV_NAME% is ready.
