@echo off
setlocal enabledelayedexpansion
title Event Insight Launcher

echo ======================================================================
echo          EVENT INSIGHT - College Event Feedback Analyzer
echo ======================================================================
echo.

:: Detect project root directory
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%college-event-feedback-analyzer\backend\app\main.py" (
    set "PROJECT_ROOT=%SCRIPT_DIR%college-event-feedback-analyzer"
) else if exist "%SCRIPT_DIR%backend\app\main.py" (
    set "PROJECT_ROOT=%SCRIPT_DIR%"
) else (
    echo [ERROR] Could not locate backend/app/main.py!
    echo Please ensure run.bat is placed in the project folder.
    pause
    exit /b 1
)

echo [1/3] Checking Python installation...
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not found in system PATH.
        echo Please install Python 3.9+ from https://www.python.org/
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py"
    )
) else (
    set "PY_CMD=python"
)

echo       Using Python interpreter: %PY_CMD%
echo.

echo [2/3] Launching FastAPI Backend on http://localhost:8800 ...
start "Event Insight - Backend API (Port 8800)" cmd /k "title Backend API (Port 8800) && cd /d "%PROJECT_ROOT%\backend" && echo Starting FastAPI backend on http://localhost:8800 ... && %PY_CMD% -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8800"

echo [3/3] Launching Frontend Server on http://localhost:3300 ...
start "Event Insight - Frontend (Port 3300)" cmd /k "title Frontend Server (Port 3300) && cd /d "%PROJECT_ROOT%\frontend" && echo Serving frontend on http://localhost:3300 ... && %PY_CMD% -m http.server 3300 --bind 127.0.0.1"

echo.
echo Waiting for servers to initialize...
timeout /t 3 /nobreak >nul

echo Opening browser at http://localhost:3300 ...
start http://localhost:3300

echo.
echo ======================================================================
echo               Event Insight is now running!
echo ======================================================================
echo.
echo   * Web Dashboard:  http://localhost:3300
echo   * Backend API:    http://localhost:8800
echo   * API Docs:       http://localhost:8800/docs
echo.
echo   Default Login Credentials:
echo   --------------------------------------------------
echo   * Admin:   admin   /  Admin@Event123
echo   * Viewer:  viewer  /  Viewer@Event123
echo.
echo ======================================================================
echo Keep the backend and frontend terminal windows open while using the app.
echo You may close this launcher window now.
echo ======================================================================
echo.
pause
