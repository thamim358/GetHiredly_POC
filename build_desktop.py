#!/usr/bin/env python3
"""
LinkedIn AutoBot Desktop Builder
Creates standalone executable for distribution
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
import json

class DesktopBuilder:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.dist_dir = self.base_dir / "dist"
        self.build_dir = self.base_dir / "build"
        self.output_dir = self.base_dir / "release"
        
    def clean_previous_builds(self):
        """Clean previous build artifacts"""
        print("🧹 Cleaning previous builds...")
        
        # Remove build directories
        for dir_path in [self.dist_dir, self.build_dir, self.output_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   Removed: {dir_path}")
        
        # Remove spec files
        for spec_file in self.base_dir.glob("*.spec"):
            spec_file.unlink()
            print(f"   Removed: {spec_file}")
    
    def prepare_resources(self):
        """Prepare additional resources for bundling"""
        print("📦 Preparing resources...")
        
        # Create resources directory
        resources_dir = self.base_dir / "resources"
        resources_dir.mkdir(exist_ok=True)
        
        # Copy ChromeDriver
        chromedriver_src = self.base_dir / "setup" / "chromedriver" / "chromedriver.exe"
        if chromedriver_src.exists():
            shutil.copy2(chromedriver_src, resources_dir / "chromedriver.exe")
            print("   ✅ ChromeDriver copied")
        else:
            print("   ⚠️ ChromeDriver not found, will need manual installation")
        
        # Copy templates and static files
        for folder in ["templates", "static"]:
            src_folder = self.base_dir / folder
            if src_folder.exists():
                dest_folder = resources_dir / folder
                if dest_folder.exists():
                    shutil.rmtree(dest_folder)
                shutil.copytree(src_folder, dest_folder)
                print(f"   ✅ {folder} copied")
        
        return resources_dir
    
    def create_spec_file(self):
        """Create PyInstaller spec file with custom configuration"""
        print("📄 Creating PyInstaller spec file...")
        
        spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Define paths
base_dir = Path(SPECPATH)
resources_dir = base_dir / "resources"

# Data files to include
datas = []

# Add templates if they exist
templates_dir = resources_dir / "templates"
if templates_dir.exists():
    datas.append((str(templates_dir), "templates"))

# Add static files if they exist
static_dir = resources_dir / "static"
if static_dir.exists():
    datas.append((str(static_dir), "static"))

# Add ChromeDriver
chromedriver_path = resources_dir / "chromedriver.exe"
if chromedriver_path.exists():
    datas.append((str(chromedriver_path), "drivers"))

# Hidden imports for all modules
hiddenimports = [
    'flask',
    'flask_cors',
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.chrome.service',
    'selenium.webdriver.chrome.options',
    'selenium.webdriver.common.by',
    'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions',
    'selenium.common.exceptions',
    'pandas',
    'openpyxl',
    'PIL',
    'requests',
    'json',
    'csv',
    'datetime',
    'threading',
    'subprocess',
    'tempfile',
    'zipfile',
    'logging',
    'time',
    'os',
    'sys',
    'pathlib'
]

a = Analysis(
    ['professional_dashboard_api.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LinkedInAutoBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico' if (Path(SPECPATH) / 'resources' / 'icon.ico').exists() else None,
)
'''
        
        spec_file = self.base_dir / "linkedin_autobot.spec"
        with open(spec_file, 'w') as f:
            f.write(spec_content)
        
        print(f"   ✅ Spec file created: {spec_file}")
        return spec_file
    
    def build_executable(self):
        """Build the standalone executable"""
        print("🔨 Building executable...")
        
        # Create spec file
        spec_file = self.create_spec_file()
        
        # Run PyInstaller
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            str(spec_file)
        ]
        
        print(f"   Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ Executable built successfully!")
            return self.dist_dir / "LinkedInAutoBot.exe"
        else:
            print(f"   ❌ Build failed:")
            print(f"   STDOUT: {result.stdout}")
            print(f"   STDERR: {result.stderr}")
            return None
    
    def create_portable_package(self, exe_path):
        """Create portable package with all necessary files"""
        print("📦 Creating portable package...")
        
        self.output_dir.mkdir(exist_ok=True)
        package_dir = self.output_dir / "LinkedInAutoBot_Portable"
        package_dir.mkdir(exist_ok=True)
        
        # Copy executable
        shutil.copy2(exe_path, package_dir / "LinkedInAutoBot.exe")
        
        # Create config directory
        config_dir = package_dir / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Copy configuration files (without sensitive data)
        config_files = [
            "config/settings.py",
            "config/questions.py"
        ]
        
        for config_file in config_files:
            src_file = self.base_dir / config_file
            if src_file.exists():
                shutil.copy2(src_file, config_dir)
        
        # Create README for users
        readme_content = """
# LinkedIn AutoBot Professional - Desktop Edition

## Quick Start Guide

1. **First Time Setup:**
   - Run LinkedInAutoBot.exe as Administrator
   - The application will open in your default browser
   - Navigate to: http://localhost:5000

2. **Chrome Browser Requirement:**
   - Ensure Google Chrome is installed
   - The application will automatically detect Chrome

3. **Usage:**
   - Configure your profile in the dashboard
   - Upload your resume
   - Set up job search criteria
   - Start automation

4. **Data Location:**
   - All data is stored locally in this folder
   - Logs: ./logs/
   - Exports: ./exports/
   - Uploads: ./uploads/

5. **Support:**
   - For support, contact: support@yourcompany.com
   - License key required for full functionality

## License Information
This software is licensed for single-user use.
License Key: [Enter your license key in the application]

## System Requirements
- Windows 10/11
- Google Chrome Browser
- Internet Connection
- 4GB RAM (recommended)
- 500MB Disk Space

Version: 2.0
Build Date: """ + str(Path(__file__).stat().st_mtime) + """
        """
        
        with open(package_dir / "README.txt", 'w') as f:
            f.write(readme_content.strip())
        
        # Create batch file for easy startup
        batch_content = """@echo off
echo Starting LinkedIn AutoBot Professional...
echo.
echo Dashboard will open at: http://localhost:5000
echo.
echo Close this window to stop the application
echo.
LinkedInAutoBot.exe
pause
"""
        
        with open(package_dir / "Start_LinkedInAutoBot.bat", 'w') as f:
            f.write(batch_content)
        
        print(f"   ✅ Portable package created: {package_dir}")
        return package_dir
    
    def create_zip_distribution(self, package_dir):
        """Create ZIP file for distribution"""
        print("🗜️ Creating ZIP distribution...")
        
        zip_path = self.output_dir / "LinkedInAutoBot_Professional_v2.0.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(package_dir.parent)
                    zipf.write(file_path, arcname)
        
        print(f"   ✅ ZIP created: {zip_path}")
        print(f"   📏 Size: {zip_path.stat().st_size / (1024*1024):.1f} MB")
        return zip_path
    
    def build_all(self):
        """Complete build process"""
        print("🚀 Starting LinkedIn AutoBot Desktop Build Process")
        print("=" * 60)
        
        try:
            # Step 1: Clean previous builds
            self.clean_previous_builds()
            
            # Step 2: Prepare resources
            self.prepare_resources()
            
            # Step 3: Build executable
            exe_path = self.build_executable()
            if not exe_path:
                print("❌ Build failed!")
                return False
            
            # Step 4: Create portable package
            package_dir = self.create_portable_package(exe_path)
            
            # Step 5: Create ZIP distribution
            zip_path = self.create_zip_distribution(package_dir)
            
            print("\n" + "=" * 60)
            print("🎉 BUILD COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"📁 Portable Package: {package_dir}")
            print(f"📦 ZIP Distribution: {zip_path}")
            print(f"💾 Total Size: {zip_path.stat().st_size / (1024*1024):.1f} MB")
            print("\n✅ Ready for distribution!")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Build failed with error: {e}")
            return False

def main():
    """Main build function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--clean-only":
        builder = DesktopBuilder()
        builder.clean_previous_builds()
        return
    
    builder = DesktopBuilder()
    success = builder.build_all()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Test the executable on a clean Windows machine")
        print("2. Set up licensing system")
        print("3. Create installer (optional)")
        print("4. Upload to distribution platform")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()