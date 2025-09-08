@echo off
echo.
echo ================================
echo   LinkedIn AutoBot Dashboard
echo ================================
echo.
echo Starting dashboard server...
echo.
echo Dashboard will be available at:
echo http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Install required packages if not already installed
REM python -m pip install flask flask-cors pandas openpyxl --quiet

REM Start the dashboard API server
python dashboard_api.py

pause
