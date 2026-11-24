@echo off
cd /d "%~dp0"
echo.
echo ================================
echo   LinkedIn Career Assistant
echo ================================
echo.
echo Starting dashboard server...
echo.
echo Dashboard will be available at:
echo http://127.0.0.1:5000/dashboard
echo.
echo Press Ctrl+C to stop the server
echo.

REM Use the project's virtual environment when it is available.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" professional_dashboard_api.py
) else (
    python professional_dashboard_api.py
)

pause
