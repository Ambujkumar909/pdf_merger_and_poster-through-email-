@echo off

REM Set paths and environment variables
set PROJECT_DIR=%~dp0
set VENV_NAME=pdf_merger_with_email
set VENV_DIR=%PROJECT_DIR%%VENV_NAME%

REM Check if virtual environment exists and activate it
if exist "%VENV_DIR%\Scripts\activate" (
    call "%VENV_DIR%\Scripts\activate"
) else (
    echo Virtual environment %VENV_NAME% not found or activated. Exiting.
    exit /b 1
)

REM Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development

REM Run Flask application
start "" python -m flask run

REM Open browser after a short delay
timeout /t 2 > nul
start "" http://127.0.0.1:5000
