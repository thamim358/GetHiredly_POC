#!/usr/bin/env python3
"""
Desktop WebDriver Manager
Handles ChromeDriver detection, download, and management for desktop distribution
"""

import os
import sys
import platform
import requests
import zipfile
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
import logging

class DesktopWebDriverManager:
    def __init__(self):
        # Set up logging first
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.base_dir = self._get_base_directory()
        self.drivers_dir = self.base_dir / "drivers"
        self.drivers_dir.mkdir(exist_ok=True)
        
        # Chrome browser paths by OS
        self.chrome_paths = {
            'windows': [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{username}\AppData\Local\Google\Chrome\Application\chrome.exe"
            ],
            'darwin': [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            ],
            'linux': [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium"
            ]
        }
    
    def _get_base_directory(self):
        """Get base directory - handles both development and executable"""
        if getattr(sys, 'frozen', False):
            # Running as executable (PyInstaller)
            # Use the directory where the executable is located for drivers
            base_path = Path(sys.executable).parent
            self.logger.info(f"Running as executable, base path: {base_path}")
            return base_path
        else:
            # Running as script
            script_path = Path(__file__).parent
            self.logger.info(f"Running as script, base path: {script_path}")
            return script_path
    
    def get_chrome_version(self):
        """Detect installed Chrome version"""
        try:
            chrome_path = self._find_chrome_executable()
            if not chrome_path:
                return None
            
            if self.system == 'windows':
                # Windows: Get version from file properties using powershell
                chrome_path_str = str(chrome_path).replace("\\", "\\\\")
                cmd = f'powershell -Command "(Get-ItemProperty \'{chrome_path_str}\').VersionInfo.ProductVersion"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    version = result.stdout.strip()
                    # Extract major version
                    major_version = version.split('.')[0]
                    self.logger.info(f"Detected Chrome version: {version} (major: {major_version})")
                    return major_version
                
                # Fallback method for Windows
                try:
                    cmd = f'"{chrome_path}" --version'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        version_line = result.stdout.strip()
                        # Extract version number
                        import re
                        match = re.search(r'(\d+)\.', version_line)
                        if match:
                            major_version = match.group(1)
                            self.logger.info(f"Detected Chrome version (fallback): {version_line} (major: {major_version})")
                            return major_version
                except:
                    pass
            
            elif self.system == 'darwin':
                # macOS: Get version from Info.plist
                plist_path = chrome_path.parent.parent / "Info.plist"
                if plist_path.exists():
                    cmd = f"defaults read '{plist_path}' CFBundleShortVersionString"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        return version.split('.')[0]  # Major version
            
            elif self.system == 'linux':
                # Linux: Run chrome with version flag
                cmd = f'"{chrome_path}" --version'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    version_line = result.stdout.strip()
                    # Extract version number
                    import re
                    match = re.search(r'(\d+)\.', version_line)
                    if match:
                        return match.group(1)
            
        except Exception as e:
            self.logger.warning(f"Could not detect Chrome version: {e}")
        
        return None
    
    def _find_chrome_executable(self):
        """Find Chrome executable on the system"""
        possible_paths = self.chrome_paths.get(self.system, [])
        
        for path_template in possible_paths:
            if '{username}' in path_template:
                import getpass
                path = path_template.format(username=getpass.getuser())
            else:
                path = path_template
            
            path_obj = Path(path)
            if path_obj.exists():
                return path_obj
        
        return None
    
    def get_chromedriver_path(self):
        """Get ChromeDriver executable path"""
        if self.system == 'windows':
            driver_name = "chromedriver.exe"
        else:
            driver_name = "chromedriver"
        
        # Check bundled driver first
        bundled_driver = self.drivers_dir / driver_name
        if bundled_driver.exists():
            return str(bundled_driver)
        
        # Check if ChromeDriver is in PATH
        driver_in_path = shutil.which("chromedriver")
        if driver_in_path:
            return driver_in_path
        
        # Auto-download if not found
        downloaded_driver = self.download_chromedriver()
        if downloaded_driver:
            return str(downloaded_driver)
        
        return None
    
    def download_chromedriver(self):
        """Download appropriate ChromeDriver version"""
        try:
            print("📥 Downloading ChromeDriver for your system...")
            print("This may take a moment, please wait...")
            self.logger.info("📥 Downloading ChromeDriver...")
            
            # Get Chrome version
            chrome_version = self.get_chrome_version()
            if not chrome_version:
                print("⚠️ Could not detect Chrome version, using latest ChromeDriver")
                self.logger.warning("Could not detect Chrome version, using latest ChromeDriver")
                chrome_version = "latest"
            else:
                print(f"📊 Detected Chrome version: {chrome_version}")
            
            # Get ChromeDriver download URL
            driver_url = self._get_chromedriver_url(chrome_version)
            if not driver_url:
                print("❌ Could not find ChromeDriver download URL")
                self.logger.error("Could not find ChromeDriver download URL")
                return None
            
            print(f"🌐 Downloading from: {driver_url}")
            
            # Download ChromeDriver with progress feedback
            response = requests.get(driver_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r⬇️ Download progress: {progress:.1f}%", end='', flush=True)
                temp_zip_path = temp_file.name
            
            print("\n📦 Extracting ChromeDriver...")
            
            # Extract ChromeDriver
            driver_path = self._extract_chromedriver(temp_zip_path)
            
            # Clean up temporary file
            os.unlink(temp_zip_path)
            
            if driver_path:
                print(f"✅ ChromeDriver downloaded and ready: {driver_path}")
                self.logger.info(f"✅ ChromeDriver downloaded: {driver_path}")
                return driver_path
            else:
                print("❌ Failed to extract ChromeDriver")
                self.logger.error("Failed to extract ChromeDriver")
                return None
                
        except Exception as e:
            print(f"❌ Failed to download ChromeDriver: {e}")
            self.logger.error(f"Failed to download ChromeDriver: {e}")
            return None
    
    def _get_chromedriver_url(self, chrome_version):
        """Get ChromeDriver download URL for the specified Chrome version"""
        try:
            # For Chrome 115+ (newer versions), use Chrome for Testing API first
            if chrome_version != "latest" and int(chrome_version) >= 115:
                testing_url = self._get_chrome_for_testing_url(chrome_version)
                if testing_url:
                    return testing_url
            
            # Fallback to legacy ChromeDriver API
            if chrome_version == "latest":
                api_url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
            else:
                api_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{chrome_version}"
            
            # Get ChromeDriver version
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                # Try Chrome for Testing API as fallback
                return self._get_chrome_for_testing_url(chrome_version)
            
            driver_version = response.text.strip()
            
            # Determine platform
            if self.system == 'windows':
                if '64' in self.arch:
                    platform_name = "win32"  # ChromeDriver uses win32 for all Windows
                else:
                    platform_name = "win32"
            elif self.system == 'darwin':
                if 'arm' in self.arch or 'aarch64' in self.arch:
                    platform_name = "mac64_m1"
                else:
                    platform_name = "mac64"
            elif self.system == 'linux':
                platform_name = "linux64"
            else:
                self.logger.error(f"Unsupported platform: {self.system}")
                return None
            
            # Construct download URL
            download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_{platform_name}.zip"
            
            return download_url
            
        except Exception as e:
            self.logger.error(f"Error getting ChromeDriver URL: {e}")
            # Try Chrome for Testing API as final fallback
            return self._get_chrome_for_testing_url(chrome_version)
    
    def _get_chrome_for_testing_url(self, chrome_version):
        """Get ChromeDriver URL from Chrome for Testing API (newer versions)"""
        try:
            api_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            versions = data.get('versions', [])
            
            # Find matching version
            target_version = None
            for version_info in reversed(versions):  # Start from latest
                if version_info['version'].startswith(chrome_version):
                    target_version = version_info
                    break
            
            if not target_version:
                self.logger.warning(f"No ChromeDriver found for Chrome version {chrome_version}")
                return None
            
            # Find download URL for our platform
            downloads = target_version.get('downloads', {}).get('chromedriver', [])
            
            # Use win64 for Windows systems (more compatible with modern Chrome)
            platform_map = {
                'windows': 'win64',  # Use win64 for Windows 64-bit systems
                'darwin': 'mac-arm64' if 'arm' in self.arch else 'mac-x64',
                'linux': 'linux64'
            }
            
            target_platform = platform_map.get(self.system)
            if not target_platform:
                return None
            
            for download in downloads:
                if download['platform'] == target_platform:
                    self.logger.info(f"Found ChromeDriver {target_version['version']} for {target_platform}")
                    return download['url']
            
            # If win32 not found for Windows, try win64 as fallback
            if self.system == 'windows':
                for download in downloads:
                    if download['platform'] == 'win64':
                        self.logger.info(f"Using win64 ChromeDriver as fallback for {target_version['version']}")
                        return download['url']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error with Chrome for Testing API: {e}")
            return None
    
    def _extract_chromedriver(self, zip_path):
        """Extract ChromeDriver from ZIP file"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find ChromeDriver executable in ZIP
                chromedriver_files = [f for f in zip_ref.namelist() 
                                    if 'chromedriver' in f.lower() and not f.endswith('/')]
                
                if not chromedriver_files:
                    self.logger.error("No ChromeDriver executable found in ZIP")
                    return None
                
                # Extract the first ChromeDriver found
                chromedriver_in_zip = chromedriver_files[0]
                
                # Determine output filename
                if self.system == 'windows':
                    output_name = "chromedriver.exe"
                else:
                    output_name = "chromedriver"
                
                output_path = self.drivers_dir / output_name
                
                # Extract file
                with zip_ref.open(chromedriver_in_zip) as source:
                    with open(output_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                
                # Make executable on Unix systems
                if self.system != 'windows':
                    os.chmod(output_path, 0o755)
                
                return output_path
                
        except Exception as e:
            self.logger.error(f"Error extracting ChromeDriver: {e}")
            return None
    
    def verify_chromedriver(self, driver_path):
        """Verify that ChromeDriver is working"""
        try:
            if not os.path.exists(driver_path):
                return False
            
            # Try to run ChromeDriver with --version
            result = subprocess.run(
                [driver_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Error verifying ChromeDriver: {e}")
            return False
    
    def setup_webdriver_fallback(self):
        """Fallback WebDriver setup using undetected-chromedriver"""
        try:
            print("🔄 Using fallback method with undetected-chromedriver...")
            self.logger.info("Using fallback WebDriver setup with undetected-chromedriver")
            
            # Check if Chrome is installed
            chrome_path = self._find_chrome_executable()
            if not chrome_path:
                print("❌ Google Chrome not found!")
                print("Please install Google Chrome from https://www.google.com/chrome/")
                return None
            
            print(f"✅ Chrome found: {chrome_path}")
            
            try:
                import undetected_chromedriver as uc
                print("✅ Undetected-chromedriver available")
                
                # Test creating a driver instance
                options = uc.ChromeOptions()
                # Don't force headless mode - let the application settings control this
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                
                # This will auto-download the correct ChromeDriver
                driver = uc.Chrome(options=options)
                driver_path = driver.service.path if hasattr(driver, 'service') else "auto-managed"
                driver.quit()
                
                print("✅ Undetected-chromedriver setup successful!")
                return {
                    'success': True,
                    'driver_path': driver_path,
                    'chrome_path': str(chrome_path),
                    'chrome_version': self.get_chrome_version(),
                    'system': self.system,
                    'method': 'undetected-chromedriver'
                }
                
            except Exception as e:
                print(f"❌ Undetected-chromedriver failed: {e}")
                return None
                
        except Exception as e:
            print(f"❌ Fallback WebDriver setup failed: {e}")
            return None
    def setup_webdriver(self):
        """Complete WebDriver setup - returns driver path or None"""
        try:
            print("🔧 Setting up WebDriver for LinkedIn automation...")
            self.logger.info("🔧 Setting up WebDriver for desktop application...")
            
            # Check if Chrome is installed
            chrome_path = self._find_chrome_executable()
            if not chrome_path:
                print("❌ Google Chrome not found!")
                print("Please install Google Chrome from https://www.google.com/chrome/")
                self.logger.error("❌ Google Chrome not found. Please install Chrome first.")
                return None
            
            print(f"✅ Chrome found: {chrome_path}")
            self.logger.info(f"✅ Chrome found: {chrome_path}")
            
            # Get Chrome version
            chrome_version = self.get_chrome_version()
            if chrome_version:
                print(f"📊 Chrome version: {chrome_version}")
            self.logger.info(f"📊 Chrome version: {chrome_version or 'Unknown'}")
            
            # Get ChromeDriver path
            print("🔍 Checking for ChromeDriver...")
            driver_path = self.get_chromedriver_path()
            if not driver_path:
                print("❌ Could not obtain ChromeDriver")
                self.logger.error("❌ Could not obtain ChromeDriver")
                
                # Try fallback method
                print("🔄 Trying fallback method...")
                return self.setup_webdriver_fallback()
            
            # Verify ChromeDriver
            print("✔️ Verifying ChromeDriver...")
            if not self.verify_chromedriver(driver_path):
                print("❌ ChromeDriver verification failed")
                self.logger.error("❌ ChromeDriver verification failed")
                
                # Try fallback method
                print("🔄 Trying fallback method...")
                return self.setup_webdriver_fallback()
            
            print(f"✅ ChromeDriver ready!")
            print("🚀 WebDriver setup complete - Chrome will open shortly...")
            self.logger.info(f"✅ ChromeDriver ready: {driver_path}")
            
            return {
                'success': True,
                'driver_path': driver_path,
                'chrome_path': str(chrome_path),
                'chrome_version': chrome_version,
                'system': self.system,
                'method': 'direct-download'
            }
            
        except Exception as e:
            print(f"❌ WebDriver setup failed: {e}")
            self.logger.error(f"WebDriver setup failed: {e}")
            
            # Try fallback method
            print("🔄 Trying fallback method...")
            return self.setup_webdriver_fallback()
    
    def get_chrome_options(self):
        """Get Chrome options optimized for desktop application"""
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        
        # Basic options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        # Remove problematic options that break LinkedIn:
        # --disable-extensions (keep some for functionality)
        # --disable-javascript (breaks LinkedIn completely)
        # --disable-images (may cause issues)
        
        # Window options
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        
        # User data directory for session persistence
        user_data_dir = self.drivers_dir.parent / "chrome_profile"
        user_data_dir.mkdir(exist_ok=True)
        options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Disable logging to reduce output
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Disable notifications and popups
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        return options


# Example usage
def main():
    """Test the WebDriver manager"""
    print("🌐 Desktop WebDriver Manager Test")
    print("=" * 40)
    
    manager = DesktopWebDriverManager()
    
    # Setup WebDriver
    result = manager.setup_webdriver()
    
    if result:
        print("\n✅ WebDriver setup successful!")
        print(f"Chrome Path: {result['chrome_path']}")
        print(f"Driver Path: {result['driver_path']}")
        print(f"Chrome Version: {result['chrome_version']}")
        print(f"System: {result['system']}")
        
        # Test Chrome options
        print("\n🔧 Testing Chrome options...")
        options = manager.get_chrome_options()
        print(f"Options configured: {len(options.arguments)} arguments")
        
    else:
        print("\n❌ WebDriver setup failed!")
        print("Please ensure Google Chrome is installed.")


if __name__ == "__main__":
    main()