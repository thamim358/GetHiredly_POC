'''
Author:     Thamim ansari
LinkedIn:   https://www.linkedin.com/in/thamim358/

Copyright (C) 2024 Thamim ansari


            


version:    24.12.29.12.30
'''

from modules.helpers import make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path
from config.questions import default_resume_path
if stealth_mode:
    import undetected_chromedriver as uc
else: 
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    # from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from modules.helpers import find_default_profile_directory, critical_error_log, print_lg

try:
    make_directories([file_name,failed_file_name,logs_folder_path+"/screenshots",default_resume_path,generated_resume_path+"/temp"])

    # Set up WebDriver with Chrome Profile
    options = uc.ChromeOptions() if stealth_mode else Options()
    
    # Add Chrome arguments to fix startup issues
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
        options.add_argument("--guest")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
    else:
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
        # try: 
        #     driver = uc.Chrome(driver_executable_path="C:\\Program Files\\Google\\Chrome\\chromedriver-win64\\chromedriver.exe", options=options)
        # except (FileNotFoundError, PermissionError) as e: 
        #     print_lg("(Undetected Mode) Got '{}' when using pre-installed ChromeDriver.".format(type(e).__name__)) 
            print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
            driver = uc.Chrome(options=options)
    else: 
        # Try multiple approaches to start Chrome
        driver = None
        attempts = 0
        max_attempts = 3
        
        while driver is None and attempts < max_attempts:
            attempts += 1
            try:
                print_lg(f"Attempting to start Chrome (attempt {attempts}/{max_attempts})...")
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
    driver.maximize_window()
    print_lg("Setting up WebDriver wait and actions...")
    wait = WebDriverWait(driver, 10)  # Increased timeout
    actions = ActionChains(driver)
    
    # Test if Chrome is responsive
    try:
        print_lg("Testing Chrome responsiveness...")
        driver.get("data:text/html,<html><body><h1>Chrome Test</h1></body></html>")
        print_lg("Chrome is responsive and ready!")
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
    
