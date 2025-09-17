'''
Author:     Thamim ansari
LinkedIn:   https://www.linkedin.com/in/thamim358/

Copyright (C) 2024 Thamim ansari


            


version:    24.12.29.12.30
'''

from modules.helpers import make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path
from config.questions import default_resume_path
from pathlib import Path
import os
if stealth_mode:
    import undetected_chromedriver as uc
else: 
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from modules.helpers import find_default_profile_directory, critical_error_log, print_lg

# Import desktop WebDriver manager for proper ChromeDriver handling
try:
    from desktop_webdriver_manager import DesktopWebDriverManager
    desktop_manager = DesktopWebDriverManager()
    print_lg("🔧 Desktop WebDriver Manager loaded successfully")
except ImportError as e:
    print_lg(f"⚠️ Desktop WebDriver Manager not available: {e}")
    desktop_manager = None

try:
    make_directories([file_name,failed_file_name,logs_folder_path+"/screenshots",default_resume_path,generated_resume_path+"/temp"])

    # Check if running as executable and in portable mode
    import sys
    is_executable = getattr(sys, 'frozen', False)
    is_portable = os.environ.get('LINKEDIN_AUTOBOT_PORTABLE') == '1'
    
    if is_executable:
        print_lg("🔧 Running as executable - using optimized Chrome settings")
        if is_portable:
            print_lg("📦 Portable mode detected - using embedded Chrome")
    else:
        print_lg("🔧 Running as script - using standard Chrome settings")

    # Initialize portable Chrome setup if in portable mode
    portable_chrome_path = None
    portable_driver_path = None
    
    if is_portable and is_executable:
        try:
            # Get executable directory
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller temporary directory
                exe_dir = Path(sys.executable).parent
            else:
                exe_dir = Path(__file__).parent.parent
            
            # Look for portable Chrome
            chrome_dir = exe_dir / "chrome"
            
            # Find Chrome executable
            chrome_paths = [
                chrome_dir / "chrome-win64" / "chrome.exe",
                chrome_dir / "chrome.exe",
                chrome_dir / "Application" / "chrome.exe"
            ]
            
            for chrome_path in chrome_paths:
                if chrome_path.exists():
                    portable_chrome_path = str(chrome_path)
                    print_lg(f"📦 Found portable Chrome: {portable_chrome_path}")
                    break
            
            # Find ChromeDriver
            driver_paths = [
                chrome_dir / "chromedriver-win64" / "chromedriver.exe",
                chrome_dir / "chromedriver.exe"
            ]
            
            for driver_path in driver_paths:
                if driver_path.exists():
                    portable_driver_path = str(driver_path)
                    print_lg(f"📦 Found portable ChromeDriver: {portable_driver_path}")
                    break
                    
        except Exception as e:
            print_lg(f"⚠️ Portable Chrome detection failed: {e}")

    # Initialize desktop WebDriver manager
    if desktop_manager and not is_portable:
        print_lg("🔧 Setting up WebDriver using Desktop WebDriver Manager...")
        webdriver_setup = desktop_manager.setup_webdriver()
        
        if webdriver_setup and webdriver_setup.get('success'):
            print_lg(f"✅ WebDriver setup successful!")
            print_lg(f"Chrome Path: {webdriver_setup['chrome_path']}")
            print_lg(f"Driver Path: {webdriver_setup['driver_path']}")
            print_lg(f"Chrome Version: {webdriver_setup['chrome_version']}")
            
            # Use desktop manager's optimized options
            options = desktop_manager.get_chrome_options()
        else:
            print_lg("⚠️ Desktop WebDriver Manager setup failed, falling back to portable/standard setup")
            options = uc.ChromeOptions() if stealth_mode else Options()
            webdriver_setup = None
    else:
        if is_portable and portable_chrome_path:
            print_lg("📦 Using portable Chrome setup")
            options = uc.ChromeOptions() if stealth_mode else Options()
            # Set portable Chrome binary
            options.binary_location = portable_chrome_path
            webdriver_setup = {
                'success': True,
                'method': 'portable',
                'chrome_path': portable_chrome_path,
                'driver_path': portable_driver_path
            }
        else:
            print_lg("⚠️ Using standard Chrome setup (Desktop WebDriver Manager not available)")
            options = uc.ChromeOptions() if stealth_mode else Options()
            webdriver_setup = None

    # Add Chrome arguments to fix startup issues (if not using desktop manager optimized options)
    if not (desktop_manager and webdriver_setup):
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-background-media-suspend")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-prompt-on-repost")
        options.add_argument("--disable-sync")
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--ignore-ssl-errors-on-localhost")
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument("--disable-component-update")
    
    # Add experimental options to prevent crashes
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("detach", True)
    
    if run_in_background:   
        options.add_argument("--headless=new")  # Use new headless mode
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
    if disable_extensions:  
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")

    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")
    if safe_mode: 
        print_lg("SAFE MODE: Will login with a guest profile, browsing history will not be saved in the browser!")
        if not (desktop_manager and webdriver_setup):
            options.add_argument("--guest")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
    else:
        if not (desktop_manager and webdriver_setup):
            # Create unique user data directory to avoid conflicts
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            unique_data_dir = os.path.join(temp_dir, f"chrome_automation_{os.getpid()}")
            options.add_argument(f"--user-data-dir={unique_data_dir}")
            options.add_argument("--disable-session-crashed-bubble")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-restore-session-state")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            print_lg(f"Using temporary user data directory: {unique_data_dir}")
    
    if stealth_mode:
        print_lg("🔒 Using stealth mode (undetected-chromedriver)")
        print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
        driver = uc.Chrome(options=options)
    else: 
        # Use desktop manager's ChromeDriver if available
        if desktop_manager and webdriver_setup:
            print_lg(f"🚀 Using Desktop Manager method: {webdriver_setup.get('method', 'unknown')}")
            
            # Check if using undetected-chromedriver method
            if webdriver_setup.get('method') == 'undetected-chromedriver':
                print_lg("🔒 Using undetected-chromedriver (auto-managed)")
                try:
                    import undetected_chromedriver as uc
                    # Use undetected chromedriver with custom options
                    uc_options = uc.ChromeOptions()
                    
                    # Force Chrome to be visible in executable environment
                    if is_executable:
                        print_lg("🖥️ Executable mode: Forcing Chrome to be visible")
                        uc_options.add_argument("--no-sandbox")
                        uc_options.add_argument("--disable-dev-shm-usage")
                        uc_options.add_argument("--start-maximized")
                        uc_options.add_argument("--disable-blink-features=AutomationControlled")
                        uc_options.add_argument("--disable-web-security")
                        uc_options.add_argument("--disable-features=VizDisplayCompositor")
                        # Explicitly ensure Chrome window appears
                        uc_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                        uc_options.add_experimental_option('useAutomationExtension', False)
                        uc_options.add_experimental_option("detach", True)
                    else:
                        # Copy essential options to undetected chromedriver
                        if run_in_background:
                            uc_options.add_argument("--headless=new")
                        else:
                            # Ensure Chrome is visible
                            uc_options.add_argument("--no-sandbox")
                            uc_options.add_argument("--disable-dev-shm-usage")
                            uc_options.add_argument("--start-maximized")
                            uc_options.add_argument("--disable-blink-features=AutomationControlled")
                            print_lg("🖥️ Chrome will be visible (run_in_background=False)")
                    
                    if not safe_mode and not (desktop_manager and webdriver_setup):
                        import tempfile
                        import os
                        temp_dir = tempfile.gettempdir()
                        unique_data_dir = os.path.join(temp_dir, f"chrome_automation_{os.getpid()}")
                        uc_options.add_argument(f"--user-data-dir={unique_data_dir}")
                    
                    print_lg("🚀 Starting Chrome with undetected-chromedriver...")
                    driver = uc.Chrome(options=uc_options)
                    print_lg("✅ Chrome started successfully with undetected-chromedriver!")
                except Exception as e:
                    print_lg(f"❌ Undetected ChromeDriver failed: {e}")
                    driver = None
            else:
                # Use regular ChromeDriver with specified path (Desktop Manager or Portable)
                driver_path = webdriver_setup['driver_path']
                method = webdriver_setup.get('method', 'unknown')
                print_lg(f"🚀 Using {method} ChromeDriver: {driver_path}")
                
                try:
                    if portable_driver_path and webdriver_setup.get('method') == 'portable':
                        # Use portable ChromeDriver
                        service = Service(executable_path=portable_driver_path)
                        print_lg(f"📦 Starting Chrome with portable ChromeDriver: {portable_driver_path}")
                    else:
                        # Use Desktop Manager ChromeDriver
                        service = Service(executable_path=driver_path)
                        print_lg(f"🚀 Starting Chrome with Desktop Manager ChromeDriver: {driver_path}")
                    
                    driver = webdriver.Chrome(service=service, options=options)
                    print_lg("✅ Chrome started successfully!")
                except Exception as e:
                    print_lg(f"❌ ChromeDriver failed: {e}")
                    print_lg("🔄 Falling back to standard Chrome setup...")
                    driver = None
        else:
            driver = None
        
        # Fallback to standard approach if desktop manager failed or not available
        if driver is None:
            attempts = 0
            max_attempts = 3
            
            while driver is None and attempts < max_attempts:
                attempts += 1
                try:
                    print_lg(f"Attempting to start Chrome (attempt {attempts}/{max_attempts})...")
                    
                    if portable_driver_path:
                        # Use portable ChromeDriver for fallback
                        service = Service(executable_path=portable_driver_path)
                        driver = webdriver.Chrome(service=service, options=options)
                        print_lg("Chrome started successfully with portable ChromeDriver!")
                    else:
                        # Use system ChromeDriver
                        driver = webdriver.Chrome(options=options)
                        print_lg("Chrome started successfully!")
                    break
                except Exception as e:
                    print_lg(f"Attempt {attempts} failed: {str(e)}")
                    if attempts < max_attempts:
                        print_lg("Waiting 3 seconds before next attempt...")
                        import time
                        time.sleep(3)
                        # Kill any remaining chrome processes
                        import subprocess
                        try:
                            subprocess.run(["taskkill", "/f", "/im", "chrome.exe", "/t"], 
                                         capture_output=True, check=False)
                            subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe", "/t"], 
                                         capture_output=True, check=False)
                        except:
                            pass
                    else:
                        raise e
                        
            if driver is None:
                raise Exception("Failed to start Chrome after multiple attempts")
    
    print_lg("Maximizing browser window...")
    try:
        driver.maximize_window()
        print_lg("✅ Browser window maximized successfully")
    except Exception as e:
        print_lg(f"⚠️ Could not maximize window: {e}")
    
    print_lg("Setting up WebDriver wait and actions...")
    wait = WebDriverWait(driver, 10)  # Increased timeout
    actions = ActionChains(driver)
    
    # Test if Chrome is responsive
    try:
        print_lg("Testing Chrome responsiveness...")
        driver.get("data:text/html,<html><body><h1>Chrome Test</h1></body></html>")
        print_lg("Chrome is responsive and ready!")
        
        # Force Chrome window to foreground in executable mode
        if is_executable:
            try:
                import win32gui
                import win32con
                def bring_to_front():
                    windows = []
                    win32gui.EnumWindows(lambda hwnd, windows: windows.append((hwnd, win32gui.GetWindowText(hwnd))), windows)
                    for hwnd, title in windows:
                        if "chrome" in title.lower():
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(hwnd)
                            print_lg(f"🔼 Brought Chrome window to foreground: {title}")
                            break
                bring_to_front()
            except ImportError:
                print_lg("⚠️ win32gui not available, cannot force window to foreground")
            except Exception as e:
                print_lg(f"⚠️ Could not bring window to foreground: {e}")
        
    except Exception as e:
        print_lg(f"Chrome responsiveness test failed: {e}")
        
    print_lg("Chrome setup completed successfully!")
except Exception as e:
    msg = 'Seems like either... \n\n1. Chrome is already running. \nA. Close all Chrome windows and try again. \n\n2. Google Chrome or Chromedriver is out dated. \nA. Update browser and Chromedriver (You can run "windows-setup.bat" in /setup folder for Windows PC to update Chromedriver)! \n\n3. If error occurred when using "stealth_mode", try reinstalling undetected-chromedriver. \nA. Open a terminal and use commands "pip uninstall undetected-chromedriver" and "pip install undetected-chromedriver". \n\n\nIf issue persists, try Safe Mode. Set, safe_mode = True in config.py \n\nPlease check GitHub discussions/support for solutions https://github.com/GodsScion/Auto_job_applier_linkedIn \n                                   OR \nReach out in discord ( https://discord.gg/fFp7uUzWCY )'
    if isinstance(e,TimeoutError): msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
    print_lg(msg)
    critical_error_log("In Opening Chrome", e)
    from pyautogui import alert
    alert(msg, "Error in opening chrome")
    try: driver.quit()
    except NameError: exit()
    
