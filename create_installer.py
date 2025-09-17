#!/usr/bin/env python3
"""
Installer Builder for LinkedIn AutoBot Professional
Creates professional Windows installer using NSIS
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import tempfile

class InstallerBuilder:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.dist_dir = self.base_dir / "dist"
        self.installer_dir = self.base_dir / "installer_build"
        self.nsis_script = self.base_dir / "installer.nsi"
        
        # NSIS paths (update these for your system)
        self.nsis_paths = [
            r"C:\Program Files (x86)\NSIS\makensis.exe",
            r"C:\Program Files\NSIS\makensis.exe",
            r"C:\NSIS\makensis.exe"
        ]
    
    def check_nsis(self):
        """Check if NSIS is installed"""
        for nsis_path in self.nsis_paths:
            if Path(nsis_path).exists():
                print(f"✅ NSIS found at: {nsis_path}")
                return nsis_path
        
        print("❌ NSIS not found!")
        print("\n📥 Please install NSIS:")
        print("1. Download from: https://nsis.sourceforge.io/Download")
        print("2. Install NSIS")
        print("3. Run this script again")
        return None
    
    def check_prerequisites(self):
        """Check if all prerequisites are available"""
        print("🔍 Checking prerequisites...")
        
        # Check if executable exists
        exe_path = self.dist_dir / "LinkedInAutoBot.exe"
        if not exe_path.exists():
            print(f"❌ Executable not found: {exe_path}")
            print("Please run 'python build_desktop.py' first")
            return False
        
        print(f"✅ Executable found: {exe_path}")
        
        # Check NSIS
        nsis_path = self.check_nsis()
        if not nsis_path:
            return False
        
        # Check required files
        required_files = [
            "templates",
            "static", 
            "README.md"
        ]
        
        missing_files = []
        for file_name in required_files:
            file_path = self.base_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
            else:
                print(f"✅ Found: {file_name}")
        
        if missing_files:
            print(f"❌ Missing files: {', '.join(missing_files)}")
            return False
        
        return True
    
    def prepare_installer_files(self):
        """Prepare all files needed for the installer"""
        print("📦 Preparing installer files...")
        
        # Clean and create installer directory
        if self.installer_dir.exists():
            shutil.rmtree(self.installer_dir)
        self.installer_dir.mkdir()
        
        # Copy executable
        exe_src = self.dist_dir / "LinkedInAutoBot.exe"
        exe_dst = self.installer_dir / "dist"
        exe_dst.mkdir()
        shutil.copy2(exe_src, exe_dst / "LinkedInAutoBot.exe")
        print("  ✅ Copied executable")
        
        # Copy templates
        templates_src = self.base_dir / "templates"
        templates_dst = self.installer_dir / "templates"
        shutil.copytree(templates_src, templates_dst)
        print("  ✅ Copied templates")
        
        # Copy static files
        static_src = self.base_dir / "static"
        if static_src.exists():
            static_dst = self.installer_dir / "static"
            shutil.copytree(static_src, static_dst)
            print("  ✅ Copied static files")
        
        # Copy ChromeDriver
        chromedriver_src = self.base_dir / "setup" / "chromedriver" / "chromedriver.exe"
        if chromedriver_src.exists():
            chromedriver_dst = self.installer_dir / "setup" / "chromedriver"
            chromedriver_dst.mkdir(parents=True)
            shutil.copy2(chromedriver_src, chromedriver_dst / "chromedriver.exe")
            print("  ✅ Copied ChromeDriver")
        
        # Copy config files (without sensitive data)
        config_src = self.base_dir / "config"
        if config_src.exists():
            config_dst = self.installer_dir / "config"
            config_dst.mkdir()
            
            # Copy only safe config files
            safe_configs = ["settings.py", "questions.py"]
            for config_file in safe_configs:
                src_file = config_src / config_file
                if src_file.exists():
                    shutil.copy2(src_file, config_dst)
            print("  ✅ Copied config files")
        
        # Create README for users
        self.create_user_readme()
        
        # Create license file
        self.create_license_file()
        
        # Create icon if it doesn't exist
        self.create_icon()
        
        print("✅ Installer files prepared")
        return True
    
    def create_user_readme(self):
        """Create user-friendly README"""
        readme_content = """
# LinkedIn AutoBot Professional - Desktop Edition

## Welcome to LinkedIn AutoBot Professional!

Thank you for purchasing LinkedIn AutoBot Professional. This powerful tool will help you automate your LinkedIn job applications and networking activities.

## Quick Start Guide

### 1. First Launch
- Double-click the "LinkedIn AutoBot Professional" icon on your desktop
- Or use Start Menu → LinkedIn AutoBot Professional
- The application will start and open in your web browser at: http://localhost:5000

### 2. Initial Setup
- Configure your personal information
- Upload your resume (PDF format recommended)
- Set up your job search criteria
- Enter your LinkedIn credentials (stored securely on your computer)

### 3. Choose Your Automation Mode
- **Email Extractor**: Find and contact hiring managers directly
- **AI Job Applier**: Automatically apply to jobs on LinkedIn
- **Combined Mode**: Use both features together

### 4. Monitor Progress
- View real-time statistics in the dashboard
- Export your application history
- Review logs and screenshots

## System Requirements
- Windows 10 or later
- Google Chrome browser (required)
- Internet connection
- 4GB RAM (recommended)
- 500MB free disk space

## Important Notes
- **Chrome Browser**: Google Chrome must be installed for the automation to work
- **Antivirus**: Add the installation folder to your antivirus whitelist if needed
- **Firewall**: Allow the application through Windows Firewall when prompted
- **License**: This software is licensed for single-user use only

## Data Storage
All your data is stored locally on your computer:
- Configuration: Stored in the application folder
- Logs: Available in the "logs" subfolder  
- Exports: Saved to the "exports" subfolder
- Uploads: Resume files stored in "uploads" subfolder

## Support & Updates
- Email: support@yourcompany.com
- Website: https://yourwebsite.com
- License Key: Required for full functionality

## License Information
This software is protected by licensing. Your license key is tied to this computer's hardware.

**License Type**: Professional Edition
**Users**: Single User
**Duration**: As specified in your purchase

## Troubleshooting

### Common Issues:
1. **"Chrome not found"** - Install Google Chrome from google.com/chrome
2. **"Port already in use"** - Close other instances of the application
3. **"License invalid"** - Check your internet connection and license key
4. **Slow performance** - Close unnecessary browser tabs and applications

### Getting Help:
1. Check the application logs in the "logs" folder
2. Try restarting the application
3. Contact support with your license key and error details

## Version Information
Version: 2.0.0
Build Date: 2025
License: Commercial

---
© 2025 Your Company Name. All rights reserved.
LinkedIn AutoBot Professional is not affiliated with LinkedIn Corporation.
        """
        
        readme_path = self.installer_dir / "README.txt"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content.strip())
        
        print("  ✅ Created user README")
        
    def create_license_file(self):
        """Create license agreement file"""
        license_content = """
SOFTWARE LICENSE AGREEMENT
LinkedIn AutoBot Professional

IMPORTANT - READ CAREFULLY: This License Agreement ("Agreement") is a legal agreement between you (either an individual or a single entity) and [Your Company Name] for the LinkedIn AutoBot Professional software product identified above, which includes computer software and may include associated media, printed materials, and "online" or electronic documentation ("SOFTWARE PRODUCT").

By installing, copying, or otherwise using the SOFTWARE PRODUCT, you agree to be bound by the terms of this Agreement. If you do not agree to the terms of this Agreement, do not install or use the SOFTWARE PRODUCT.

1. GRANT OF LICENSE
The SOFTWARE PRODUCT is licensed, not sold. This Agreement grants you the following rights:
- Installation and Use: You may install and use one copy of the SOFTWARE PRODUCT on a single computer.
- Storage/Network Use: You may store or install a copy of the SOFTWARE PRODUCT on a storage device but may only run the SOFTWARE PRODUCT on one computer at a time.

2. RESTRICTIONS
- You may NOT reverse engineer, decompile, or disassemble the SOFTWARE PRODUCT.
- You may NOT rent, lease, or lend the SOFTWARE PRODUCT.
- You may NOT distribute copies of the SOFTWARE PRODUCT to third parties.
- You may NOT remove any proprietary notices or labels on the SOFTWARE PRODUCT.

3. COPYRIGHT
All title and copyrights in and to the SOFTWARE PRODUCT are owned by [Your Company Name]. The SOFTWARE PRODUCT is protected by copyright laws and international treaty provisions.

4. LIMITED WARRANTY
The SOFTWARE PRODUCT is provided "AS IS" without warranty of any kind. [Your Company Name] disclaims all warranties, either express or implied, including but not limited to implied warranties of merchantability and fitness for a particular purpose.

5. LIMITATION OF LIABILITY
In no event shall [Your Company Name] be liable for any damages whatsoever arising out of the use of or inability to use this SOFTWARE PRODUCT.

6. TERMINATION
This Agreement is effective until terminated. You may terminate it at any time by destroying the SOFTWARE PRODUCT and all copies thereof. This Agreement will also terminate if you fail to comply with any term or condition of this Agreement.

7. GOVERNING LAW
This Agreement shall be governed by the laws of [Your Jurisdiction].

If you have any questions concerning this Agreement, contact:
[Your Company Name]
Email: support@yourcompany.com
Website: https://yourwebsite.com

© 2025 [Your Company Name]. All rights reserved.
        """
        
        license_path = self.installer_dir / "LICENSE.txt"
        with open(license_path, 'w', encoding='utf-8') as f:
            f.write(license_content.strip())
        
        print("  ✅ Created license file")
    
    def create_icon(self):
        """Create or copy application icon"""
        icon_dst = self.installer_dir / "resources"
        icon_dst.mkdir(exist_ok=True)
        
        # Check if icon exists
        possible_icons = [
            self.base_dir / "icon.ico",
            self.base_dir / "resources" / "icon.ico",
            self.base_dir / "static" / "icon.ico"
        ]
        
        icon_found = False
        for icon_path in possible_icons:
            if icon_path.exists():
                shutil.copy2(icon_path, icon_dst / "icon.ico")
                print("  ✅ Copied application icon")
                icon_found = True
                break
        
        if not icon_found:
            print("  ⚠️ No icon found - installer will use default")
    
    def build_installer(self):
        """Build the NSIS installer"""
        print("🔨 Building installer...")
        
        # Get NSIS path
        nsis_path = self.check_nsis()
        if not nsis_path:
            return False
        
        # Copy NSIS script to installer directory
        script_dst = self.installer_dir / "installer.nsi"
        shutil.copy2(self.nsis_script, script_dst)
        
        # Build installer
        cmd = [nsis_path, str(script_dst)]
        
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(self.installer_dir), 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Installer built successfully!")
            
            # Find the created installer
            installer_files = list(self.installer_dir.glob("*.exe"))
            if installer_files:
                installer_path = installer_files[0]
                
                # Move installer to release directory
                release_dir = self.base_dir / "release"
                release_dir.mkdir(exist_ok=True)
                
                final_installer = release_dir / "LinkedInAutoBot_Professional_Setup.exe"
                shutil.move(installer_path, final_installer)
                
                print(f"📦 Installer saved: {final_installer}")
                print(f"📏 Size: {final_installer.stat().st_size / (1024*1024):.1f} MB")
                
                return final_installer
            else:
                print("❌ Installer file not found after build")
                return False
        else:
            print(f"❌ NSIS build failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
    
    def create_installer(self):
        """Complete installer creation process"""
        print("🚀 Creating LinkedIn AutoBot Professional Installer")
        print("=" * 60)
        
        try:
            # Check prerequisites
            if not self.check_prerequisites():
                return False
            
            # Prepare files
            if not self.prepare_installer_files():
                return False
            
            # Build installer
            installer_path = self.build_installer()
            if not installer_path:
                return False
            
            print("\n" + "=" * 60)
            print("🎉 INSTALLER CREATED SUCCESSFULLY!")
            print("=" * 60)
            print(f"📦 Installer: {installer_path}")
            print(f"💾 Size: {installer_path.stat().st_size / (1024*1024):.1f} MB")
            
            print("\n✅ Ready for distribution!")
            print("\n🔧 Next steps:")
            print("1. Test the installer on a clean Windows machine")
            print("2. Code sign the installer (optional but recommended)")
            print("3. Upload to your distribution platform")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Installer creation failed: {e}")
            return False

def main():
    """Main installer builder function"""
    builder = InstallerBuilder()
    success = builder.create_installer()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()