#!/usr/bin/env python3
"""
Portable Desktop Builder for LinkedIn AutoBot Professional
Creates a fully self-contained executable with Chrome browser included
"""

import os
import sys
import subprocess
import shutil
import requests
import zipfile
import json
from pathlib import Path
import tempfile

class PortableBuilder:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.dist_dir = self.base_dir / "dist"
        self.build_dir = self.base_dir / "build"
        self.release_dir = self.base_dir / "release"
        self.portable_dir = self.release_dir / "LinkedInAutoBot_Portable"
        
    def print_step(self, title):
        """Print formatted step title"""
        print("\n" + "="*60)
        print(f"STEP: {title}")
        print("="*60)
    
    def clean_build(self):
        """Clean previous builds"""
        self.print_step("Clean Build")
        
        for dir_path in [self.dist_dir, self.build_dir, self.release_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"  Removed: {dir_path}")
        
        print("  Build directories cleaned")
        return True
    
    def download_chrome_portable(self):
        """Download Chrome portable for embedding"""
        self.print_step("Download Chrome Portable")
        
        chrome_dir = self.portable_dir / "chrome"
        chrome_dir.mkdir(parents=True, exist_ok=True)
        
        # Download Chrome for Testing (stable version)
        try:
            print("  Fetching Chrome for Testing API...")
            api_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            stable_version = data['channels']['Stable']['version']
            chrome_url = None
            chromedriver_url = None
            
            # Find Windows 64-bit downloads
            for download in data['channels']['Stable']['downloads'].get('chrome', []):
                if download['platform'] == 'win64':
                    chrome_url = download['url']
                    break
                    
            for download in data['channels']['Stable']['downloads'].get('chromedriver', []):
                if download['platform'] == 'win64':
                    chromedriver_url = download['url']
                    break
            
            if not chrome_url or not chromedriver_url:
                raise Exception("Could not find Chrome/ChromeDriver download URLs")
            
            print(f"  Chrome Version: {stable_version}")
            print(f"  Chrome URL: {chrome_url}")
            print(f"  ChromeDriver URL: {chromedriver_url}")
            
            # Download Chrome
            print("  Downloading Chrome...")
            chrome_zip = chrome_dir / "chrome.zip"
            with requests.get(chrome_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(chrome_zip, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Extract Chrome
            print("  Extracting Chrome...")
            with zipfile.ZipFile(chrome_zip, 'r') as zip_ref:
                zip_ref.extractall(chrome_dir)
            chrome_zip.unlink()  # Remove zip file
            
            # Download ChromeDriver
            print("  Downloading ChromeDriver...")
            driver_zip = chrome_dir / "chromedriver.zip"
            with requests.get(chromedriver_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(driver_zip, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Extract ChromeDriver
            print("  Extracting ChromeDriver...")
            with zipfile.ZipFile(driver_zip, 'r') as zip_ref:
                zip_ref.extractall(chrome_dir)
            driver_zip.unlink()  # Remove zip file
            
            print("  Chrome and ChromeDriver downloaded successfully")
            return True
            
        except Exception as e:
            print(f"  Failed to download Chrome: {e}")
            return False
    
    def build_executable(self):
        """Build the executable using PyInstaller"""
        self.print_step("Build Executable")
        
        # Create PyInstaller command optimized for portable deployment
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name=LinkedInAutoBot",
            "--distpath=release/LinkedInAutoBot_Portable",
            "--workpath=build/temp",
            "--specpath=build",
            f"--add-data={self.base_dir}/templates;templates",
            f"--add-data={self.base_dir}/config;config",
            f"--add-data={self.base_dir}/modules;modules",
            "--hidden-import=flask",
            "--hidden-import=flask_cors",
            "--hidden-import=selenium", 
            "--hidden-import=selenium.webdriver",
            "--hidden-import=selenium.webdriver.chrome",
            "--hidden-import=selenium.webdriver.chrome.service",
            "--hidden-import=selenium.webdriver.chrome.options",
            "--hidden-import=pandas",
            "--hidden-import=openpyxl",
            "--hidden-import=undetected_chromedriver",
            "--hidden-import=requests",
            "--hidden-import=json",
            "--hidden-import=csv",
            "--hidden-import=datetime",
            "--hidden-import=tempfile",
            "--hidden-import=subprocess",
            "--hidden-import=threading",
            "--hidden-import=logging",
            "--exclude-module=tkinter",
            "--exclude-module=matplotlib",
            "--exclude-module=PIL",
            "--exclude-module=Pillow",
            "--exclude-module=jax",
            "--exclude-module=jaxlib",
            "--exclude-module=torch",
            "--exclude-module=torchvision",
            "--exclude-module=tensorflow",
            "--exclude-module=gradio",
            "--exclude-module=imageio",
            "--exclude-module=scikit-image",
            "--exclude-module=numpy.distutils",
            "--noupx",
            "--noconfirm",
            "--console",  # Use console mode for better debugging
            "professional_dashboard_api.py"
        ]
        
        try:
            print("  Running PyInstaller...")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("  Executable built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  PyInstaller failed: {e}")
            if e.stderr:
                print(f"  STDERR: {e.stderr}")
            return False
    
    def create_launcher_script(self):
        """Create a launcher script that sets up the environment"""
        self.print_step("Create Launcher Script")
        
        launcher_content = '''@echo off
title LinkedIn AutoBot Professional
echo.
echo ================================================
echo  LinkedIn AutoBot Professional
echo  Portable Edition
echo ================================================
echo.
echo Starting LinkedIn AutoBot Professional...
echo.

REM Set environment variables for portable mode
set LINKEDIN_AUTOBOT_PORTABLE=1
set CHROME_PORTABLE_PATH=%~dp0chrome
set CHROMEDRIVER_PORTABLE_PATH=%~dp0chrome

REM Start the application
"%~dp0LinkedInAutoBot.exe"

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ================================================
    echo  An error occurred. Check the logs above.
    echo ================================================
    pause
)
'''
        
        launcher_path = self.portable_dir / "Start_LinkedInAutoBot.bat"
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        print("  Launcher script created")
        return True
    
    def create_portable_config(self):
        """Create portable configuration file"""
        self.print_step("Create Portable Configuration")
        
        config = {
            "portable_mode": True,
            "chrome_path": "./chrome",
            "chromedriver_path": "./chrome",
            "auto_update": False,
            "standalone": True,
            "version": "2.0.0"
        }
        
        config_path = self.portable_dir / "portable_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("  Portable configuration created")
        return True
    
    def copy_essential_files(self):
        """Copy essential files to the portable directory"""
        self.print_step("Copy Essential Files")
        
        # Files/directories to copy
        essential_items = [
            "templates",
            "config", 
            "README.md",
            "QUICK_START_GUIDE.md"
        ]
        
        for item in essential_items:
            src = self.base_dir / item
            dst = self.portable_dir / item
            
            if src.exists():
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    print(f"  Copied directory: {item}")
                else:
                    shutil.copy2(src, dst)
                    print(f"  Copied file: {item}")
            else:
                print(f"  Warning: {item} not found")
        
        return True
    
    def create_readme(self):
        """Create portable README"""
        self.print_step("Create Portable README")
        
        readme_content = '''# LinkedIn AutoBot Professional - Portable Edition

## Quick Start

1. **Double-click `Start_LinkedInAutoBot.bat`** to launch the application
2. **Open your web browser** and go to `http://localhost:5000`
3. **Configure your LinkedIn credentials** and job search preferences
4. **Start automation** and watch the magic happen!

## What's Included

- ✅ **LinkedIn AutoBot Professional** - Complete automation engine
- ✅ **Chrome Browser** - Embedded portable Chrome
- ✅ **ChromeDriver** - Latest compatible driver
- ✅ **All Dependencies** - No additional installations needed
- ✅ **Professional Dashboard** - Web-based control interface

## System Requirements

- Windows 10/11 (64-bit)
- 4GB RAM minimum (8GB recommended)
- 500MB free disk space
- Internet connection

## Features

### 🚀 **Professional Features**
- Automated job applications
- Smart resume matching
- Cover letter generation
- Email extraction and outreach
- Advanced filtering and targeting
- Real-time statistics and reporting

### 🔧 **Portable Benefits**
- No installation required
- No admin rights needed
- Self-contained and secure
- Portable across systems
- Clean removal (just delete folder)

## Support

For support and updates, visit: https://github.com/thamim358/LinkedIn_Auto_Applier

## License

Professional Edition - Licensed for commercial use
Copyright (C) 2024 Thamim Ansari

---
**Version 2.0.0 - Portable Edition**
'''
        
        readme_path = self.portable_dir / "README_PORTABLE.txt"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print("  Portable README created")
        return True
    
    def create_zip_distribution(self):
        """Create ZIP distribution"""
        self.print_step("Create ZIP Distribution")
        
        zip_path = self.release_dir / "LinkedInAutoBot_Professional_Portable_v2.0.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.portable_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(self.portable_dir)
                    zipf.write(file_path, arc_path)
                    
        file_size = zip_path.stat().st_size / (1024 * 1024)  # MB
        print(f"  ZIP created: {zip_path}")
        print(f"  Size: {file_size:.1f} MB")
        return True
    
    def build_all(self):
        """Build complete portable package"""
        print("="*60)
        print("LinkedIn AutoBot Professional - Portable Builder")
        print("="*60)
        
        steps = [
            ("Clean Build", self.clean_build),
            ("Download Chrome Portable", self.download_chrome_portable),
            ("Build Executable", self.build_executable),
            ("Copy Essential Files", self.copy_essential_files),
            ("Create Launcher Script", self.create_launcher_script),
            ("Create Portable Config", self.create_portable_config),
            ("Create Portable README", self.create_readme),
            ("Create ZIP Distribution", self.create_zip_distribution),
        ]
        
        for step_name, step_function in steps:
            try:
                if not step_function():
                    print(f"\n❌ FAILED: {step_name}")
                    return False
            except Exception as e:
                print(f"\n❌ ERROR in {step_name}: {e}")
                return False
        
        print("\n" + "="*60)
        print("✅ BUILD COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Portable Package: {self.portable_dir}")
        print(f"ZIP Distribution: {self.release_dir / 'LinkedInAutoBot_Professional_Portable_v2.0.zip'}")
        print("\n🎉 READY TO DISTRIBUTE!")
        print("1. Test: Run Start_LinkedInAutoBot.bat")
        print("2. Distribute: Share the ZIP file")
        print("3. Price: $97 (Portable Professional Edition)")
        
        return True

def main():
    builder = PortableBuilder()
    success = builder.build_all()
    
    if not success:
        print("\n❌ Build failed!")
        sys.exit(1)
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()