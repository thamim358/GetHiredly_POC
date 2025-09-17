@echo off
REM LinkedIn AutoBot Desktop Builder - Windows Setup
REM This script prepares the environment and builds the desktop application

echo ========================================
echo LinkedIn AutoBot Desktop Builder
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Install build requirements
echo 📦 Installing build requirements...
pip install -r build_requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install requirements
    pause
    exit /b 1
)

echo ✅ Requirements installed
echo.

REM Create icon if not exists (optional)
if not exist "resources\" mkdir resources
if not exist "resources\icon.ico" (
    echo ⚠️ No icon found. You can add icon.ico to resources\ folder
)

REM Run the build process
echo 🔨 Starting build process...
python build_desktop.py

if errorlevel 1 (
    echo ❌ Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ BUILD COMPLETED SUCCESSFULLY!
echo ========================================
echo.
echo 📁 Check the 'release' folder for your distribution files
echo.
pause