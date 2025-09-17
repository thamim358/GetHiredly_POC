#!/usr/bin/env python3
"""
Simple Desktop Builder for LinkedIn AutoBot
Fixed for Windows compatibility - no emoji characters
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import zipfile

class SimpleBuilder:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.dist_dir = self.base_dir / "dist"
        self.build_dir = self.base_dir / "build"
        self.release_dir = self.base_dir / "release"
    
    def clean_build(self):
        """Clean previous builds"""
        print("Cleaning previous builds...")
        
        for dir_path in [self.dist_dir, self.build_dir, self.release_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"  Removed: {dir_path}")
        
        print("  Build directories cleaned")
        return True
    
    def install_requirements(self):
        """Install build requirements"""
        print("Installing build requirements...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "pyinstaller", "requests", "flask", "flask-cors", 
                "selenium", "pandas", "openpyxl", "pillow"
            ], check=True, capture_output=True, text=True)
            
            print("  Requirements installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  Failed to install requirements: {e}")
            return False
    
    def build_executable(self):
        """Build the executable using PyInstaller"""
        print("Building executable...")
        
        # Create PyInstaller command with comprehensive exclusions
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name=LinkedInAutoBot",
            "--add-data=templates;templates",
            "--hidden-import=flask",
            "--hidden-import=selenium", 
            "--hidden-import=pandas",
            "--hidden-import=openpyxl",
            "--upx-exclude=vcruntime140.dll",
            "--upx-exclude=msvcp140.dll",
            "--upx-exclude=vcruntime140_1.dll",
            "--upx-exclude=msvcp140_1.dll",
            "--upx-exclude=msvcp140_2.dll",
            "--upx-exclude=api-ms-win-*.dll",
            "--exclude-module=tkinter",
            "--exclude-module=matplotlib",
            "--exclude-module=jax",
            "--exclude-module=jaxlib",
            "--exclude-module=PIL",
            "--exclude-module=Pillow",
            "--exclude-module=gradio",
            "--exclude-module=imageio",
            "--exclude-module=scikit-image",
            "--exclude-module=rembg",
            "--exclude-module=torchvision",
            "--exclude-module=torch",
            "--noupx",  # Disable UPX compression completely
            "--noconfirm",  # Don't ask for confirmation
            "professional_dashboard_api.py"
        ]
        
        try:
            print("  Running PyInstaller with PIL fixes...")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("  Executable built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  PyInstaller failed: {e}")
            print(f"  STDERR: {e.stderr}")
            return False
    
    def create_portable_package(self):
        """Create portable package"""
        print("Creating portable package...")
        
        # Check if executable exists
        exe_path = self.dist_dir / "LinkedInAutoBot.exe"
        if not exe_path.exists():
            print("  ERROR: Executable not found")
            return False
        
        # Create release directory
        self.release_dir.mkdir(exist_ok=True)
        portable_dir = self.release_dir / "LinkedInAutoBot_Professional"
        portable_dir.mkdir(exist_ok=True)
        
        # Copy executable
        shutil.copy2(exe_path, portable_dir / "LinkedInAutoBot.exe")
        
        # Create README
        readme_content = """
LinkedIn AutoBot Professional - Desktop Edition

QUICK START:
1. Double-click LinkedInAutoBot.exe
2. Open your browser to: http://localhost:5000
3. Follow the setup wizard

REQUIREMENTS:
- Windows 10 or later
- Google Chrome browser
- Internet connection

SUPPORT:
Email: support@yourcompany.com

Version: 2.0
        """
        
        with open(portable_dir / "README.txt", 'w') as f:
            f.write(readme_content.strip())
        
        # Create startup batch file
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
        
        with open(portable_dir / "Start_LinkedIn_AutoBot.bat", 'w') as f:
            f.write(batch_content)
        
        print(f"  Portable package created: {portable_dir}")
        return portable_dir
    
    def create_zip_distribution(self, package_dir):
        """Create ZIP file for easy distribution"""
        print("Creating ZIP distribution...")
        
        zip_path = self.release_dir / "LinkedInAutoBot_Professional_v2.0.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(package_dir.parent)
                    zipf.write(file_path, arcname)
        
        size_mb = zip_path.stat().st_size / (1024*1024)
        print(f"  ZIP created: {zip_path}")
        print(f"  Size: {size_mb:.1f} MB")
        return zip_path
    
    def build_all(self):
        """Complete build process"""
        print("="*60)
        print("LinkedIn AutoBot Professional - Simple Builder")
        print("="*60)
        
        steps = [
            ("Clean Build", self.clean_build),
            ("Install Requirements", self.install_requirements),
            ("Build Executable", self.build_executable),
            ("Create Portable Package", self.create_portable_package),
        ]
        
        package_dir = None
        
        for step_name, step_function in steps:
            print(f"\nStep: {step_name}")
            print("-" * 40)
            
            result = step_function()
            
            if step_name == "Create Portable Package":
                if result:
                    package_dir = result
                else:
                    print(f"\nBUILD FAILED at step: {step_name}")
                    return False
            elif not result:
                print(f"\nBUILD FAILED at step: {step_name}")
                return False
        
        # Create ZIP distribution
        if package_dir:
            print(f"\nStep: Create ZIP Distribution")
            print("-" * 40)
            zip_path = self.create_zip_distribution(package_dir)
            
            print("\n" + "="*60)
            print("BUILD COMPLETED SUCCESSFULLY!")
            print("="*60)
            print(f"Portable Package: {package_dir}")
            print(f"ZIP Distribution: {zip_path}")
            
            print(f"\nREADY TO SELL!")
            print(f"1. Test: Run {package_dir}/LinkedInAutoBot.exe")
            print(f"2. Upload: {zip_path} to Gumroad")
            print(f"3. Price: $97 (Professional Edition)")
            print(f"4. Sell: Share your Gumroad link!")
            
            return True
        else:
            print("\nBUILD INCOMPLETE!")
            return False

def main():
    builder = SimpleBuilder()
    success = builder.build_all()
    
    input(f"\nPress Enter to exit...")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()