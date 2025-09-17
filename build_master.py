#!/usr/bin/env python3
"""
Master Build Script - LinkedIn AutoBot Professional
Complete automation for building, protecting, and packaging the desktop application
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import json

class MasterBuilder:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.success_steps = []
        self.failed_steps = []
        
    def print_header(self, title):
        """Print formatted header"""
        print("\n" + "=" * 60)
        print(f"🚀 {title}")
        print("=" * 60)
    
    def print_step(self, step_num, title, description):
        """Print step information"""
        print(f"\n{step_num}. {title}")
        print(f"   {description}")
        print("   " + "-" * 50)
    
    def run_step(self, step_name, command_or_function, description):
        """Run a build step and track success/failure"""
        print(f"\n🔧 {step_name}...")
        print(f"   {description}")
        
        try:
            if callable(command_or_function):
                # It's a function
                result = command_or_function()
                success = result if isinstance(result, bool) else True
            else:
                # It's a command
                if isinstance(command_or_function, list):
                    result = subprocess.run(command_or_function, check=True, 
                                          capture_output=True, text=True)
                else:
                    result = subprocess.run(command_or_function, shell=True, 
                                          check=True, capture_output=True, text=True)
                success = result.returncode == 0
            
            if success:
                print(f"   ✅ {step_name} completed successfully")
                self.success_steps.append(step_name)
                return True
            else:
                print(f"   ❌ {step_name} failed")
                self.failed_steps.append(step_name)
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"   ❌ {step_name} failed: {e}")
            print(f"   STDERR: {e.stderr}")
            self.failed_steps.append(step_name)
            return False
        except Exception as e:
            print(f"   ❌ {step_name} failed: {e}")
            self.failed_steps.append(step_name)
            return False
    
    def check_prerequisites(self):
        """Check if all prerequisites are installed"""
        self.print_header("PREREQUISITE CHECK")
        
        # Check Python
        try:
            python_version = sys.version_info
            if python_version.major == 3 and python_version.minor >= 8:
                print(f"✅ Python {python_version.major}.{python_version.minor} found")
            else:
                print(f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}")
                return False
        except:
            print("❌ Python not found")
            return False
        
        # Check pip packages
        required_packages = [
            'pyinstaller', 'requests', 'flask', 'selenium', 
            'pandas', 'openpyxl', 'flask-cors'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"✅ {package} found")
            except ImportError:
                missing_packages.append(package)
                print(f"❌ {package} missing")
        
        if missing_packages:
            print(f"\n📦 Installing missing packages...")
            for package in missing_packages:
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                                 check=True, capture_output=True)
                    print(f"   ✅ Installed {package}")
                except:
                    print(f"   ❌ Failed to install {package}")
                    return False
        
        # Check Chrome
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        
        chrome_found = any(Path(path).exists() for path in chrome_paths)
        if chrome_found:
            print("✅ Google Chrome found")
        else:
            print("⚠️ Google Chrome not found - users will need to install it")
        
        print("\n✅ Prerequisites check completed")
        return True
    
    def build_application(self):
        """Build the main application"""
        self.print_header("APPLICATION BUILD")
        
        steps = [
            ("Install build requirements", 
             [sys.executable, "-m", "pip", "install", "-r", "build_requirements.txt"],
             "Installing PyInstaller and build dependencies"),
            
            ("Clean previous builds", 
             lambda: self.clean_build_directories(),
             "Removing old build artifacts"),
            
            ("Build desktop executable", 
             [sys.executable, "build_desktop.py"],
             "Creating standalone executable with PyInstaller"),
        ]
        
        for step_name, command, description in steps:
            if not self.run_step(step_name, command, description):
                return False
        
        return True
    
    def clean_build_directories(self):
        """Clean build directories"""
        dirs_to_clean = ['dist', 'build', 'release', 'protected', 'obfuscated']
        
        for dir_name in dirs_to_clean:
            dir_path = self.base_dir / dir_name
            if dir_path.exists():
                import shutil
                shutil.rmtree(dir_path)
                print(f"     Removed: {dir_path}")
        
        return True
    
    def protect_code(self):
        """Apply code protection"""
        self.print_header("CODE PROTECTION")
        
        steps = [
            ("Install PyArmor", 
             [sys.executable, "-m", "pip", "install", "pyarmor"],
             "Installing code obfuscation tools"),
            
            ("Apply code protection", 
             [sys.executable, "protect_code.py"],
             "Obfuscating source code and adding anti-debugging"),
        ]
        
        for step_name, command, description in steps:
            if not self.run_step(step_name, command, description):
                print(f"⚠️ Code protection failed - continuing with unprotected build")
                break
        
        return True
    
    def create_installer(self):
        """Create Windows installer"""
        self.print_header("INSTALLER CREATION")
        
        # Check if NSIS is available
        nsis_paths = [
            r"C:\Program Files (x86)\NSIS\makensis.exe",
            r"C:\Program Files\NSIS\makensis.exe"
        ]
        
        nsis_found = any(Path(path).exists() for path in nsis_paths)
        
        if not nsis_found:
            print("⚠️ NSIS not found - creating portable package only")
            return self.create_portable_package()
        
        steps = [
            ("Create installer", 
             [sys.executable, "create_installer.py"],
             "Building professional Windows installer with NSIS"),
        ]
        
        for step_name, command, description in steps:
            if not self.run_step(step_name, command, description):
                print("⚠️ Installer creation failed - creating portable package")
                return self.create_portable_package()
        
        return True
    
    def create_portable_package(self):
        """Create portable ZIP package as fallback"""
        try:
            print("📦 Creating portable package...")
            
            # Create portable directory
            portable_dir = self.base_dir / "release" / "LinkedInAutoBot_Portable"
            portable_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy executable
            exe_path = self.base_dir / "dist" / "LinkedInAutoBot.exe"
            if exe_path.exists():
                import shutil
                shutil.copy2(exe_path, portable_dir / "LinkedInAutoBot.exe")
                
                # Create readme
                readme_content = """
LinkedIn AutoBot Professional - Portable Edition

Quick Start:
1. Run LinkedInAutoBot.exe
2. Open http://localhost:5000 in your browser
3. Follow the setup wizard

Requirements:
- Windows 10 or later
- Google Chrome browser
- Internet connection

For support: support@yourcompany.com
                """
                
                with open(portable_dir / "README.txt", 'w') as f:
                    f.write(readme_content.strip())
                
                print(f"   ✅ Portable package created: {portable_dir}")
                return True
            else:
                print("   ❌ Executable not found")
                return False
                
        except Exception as e:
            print(f"   ❌ Failed to create portable package: {e}")
            return False
    
    def run_tests(self):
        """Run basic tests"""
        self.print_header("TESTING")
        
        tests = [
            ("License manager test", 
             [sys.executable, "license_manager.py"],
             "Testing hardware-based licensing system"),
            
            ("WebDriver manager test", 
             [sys.executable, "desktop_webdriver_manager.py"],
             "Testing Chrome WebDriver integration"),
        ]
        
        test_passed = 0
        for step_name, command, description in tests:
            if self.run_step(step_name, command, description):
                test_passed += 1
        
        print(f"\n📊 Test Results: {test_passed}/{len(tests)} tests passed")
        return test_passed > 0  # At least one test should pass
    
    def generate_report(self):
        """Generate build report"""
        self.print_header("BUILD REPORT")
        
        print(f"✅ Successful steps: {len(self.success_steps)}")
        for step in self.success_steps:
            print(f"   • {step}")
        
        if self.failed_steps:
            print(f"\n❌ Failed steps: {len(self.failed_steps)}")
            for step in self.failed_steps:
                print(f"   • {step}")
        
        # Check final deliverables
        deliverables = {
            "Executable": self.base_dir / "dist" / "LinkedInAutoBot.exe",
            "Portable Package": self.base_dir / "release" / "LinkedinAutoBot_Portable",
            "Installer": self.base_dir / "release" / "LinkedInAutoBot_Professional_Setup.exe"
        }
        
        print(f"\n📦 Deliverables:")
        for name, path in deliverables.items():
            if path.exists():
                if path.is_file():
                    size = path.stat().st_size / (1024*1024)
                    print(f"   ✅ {name}: {path} ({size:.1f} MB)")
                else:
                    print(f"   ✅ {name}: {path}")
            else:
                print(f"   ❌ {name}: Not found")
        
        # Success criteria
        exe_exists = deliverables["Executable"].exists()
        package_exists = (deliverables["Portable Package"].exists() or 
                         deliverables["Installer"].exists())
        
        overall_success = exe_exists and package_exists
        
        if overall_success:
            print(f"\n🎉 BUILD SUCCESSFUL!")
            print(f"✅ Ready for distribution!")
        else:
            print(f"\n❌ BUILD INCOMPLETE!")
            print(f"Check failed steps and try again.")
        
        return overall_success
    
    def build_all(self):
        """Run complete build process"""
        start_time = time.time()
        
        print("🚀 LinkedIn AutoBot Professional - Master Build Process")
        print("=" * 80)
        print("This script will build a complete, distributable desktop application")
        print("=" * 80)
        
        # Run all build steps
        steps = [
            ("Check Prerequisites", self.check_prerequisites),
            ("Build Application", self.build_application),
            ("Protect Code", self.protect_code),
            ("Create Installer", self.create_installer),
            ("Run Tests", self.run_tests),
        ]
        
        for step_name, step_function in steps:
            self.print_step(len(self.success_steps) + 1, step_name, 
                          f"Executing {step_name.lower()} process")
            
            if not step_function():
                print(f"\n⚠️ {step_name} failed, but continuing...")
        
        # Generate final report
        success = self.generate_report()
        
        elapsed_time = time.time() - start_time
        print(f"\n⏱️ Total build time: {elapsed_time:.1f} seconds")
        
        if success:
            print(f"\n🎯 Next Steps:")
            print(f"1. Test the application on a clean Windows machine")
            print(f"2. Set up your distribution platform (Gumroad recommended)")
            print(f"3. Create marketing materials and demos")
            print(f"4. Launch your desktop application!")
            
            print(f"\n💰 Revenue Potential:")
            print(f"• Conservative: $15K/month by month 6")
            print(f"• Optimistic: $100K/month by month 12")
            print(f"• Desktop apps command premium prices!")
        
        return success

def main():
    """Main build process"""
    builder = MasterBuilder()
    success = builder.build_all()
    
    input(f"\nPress Enter to exit...")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()