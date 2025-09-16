"""
Production WebDriver Configuration for Railway.app Deployment
Handles Chrome WebDriver initialization for headless operation
"""

import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_production_chrome_driver():
    """
    Create a Chrome WebDriver instance optimized for Railway.app hosting
    Returns configured WebDriver instance for headless operation
    """
    
    # Set display for X server (handled by startup script)
    if os.environ.get('ENVIRONMENT') == 'production':
        display = os.environ.get('DISPLAY', ':99')
        logger.info(f"Using X display: {display}")
    
    chrome_options = Options()
    
    # Essential headless operation arguments
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    
    # Window and display settings for LinkedIn compatibility
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--start-maximized')
    
    # LinkedIn-specific optimizations (enable some features for better compatibility)
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    # Note: Don't disable JavaScript or CSS for LinkedIn - it needs them!
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    
    # Anti-detection for LinkedIn
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    
    # Additional stability options for Railway
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--disable-client-side-phishing-detection')
    chrome_options.add_argument('--disable-crash-reporter')
    chrome_options.add_argument('--disable-oopr-debug-crash-dump')
    chrome_options.add_argument('--no-crash-upload')
    chrome_options.add_argument('--disable-low-res-tiling')
    
    # Experimental options for LinkedIn compatibility
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Set realistic user agent for LinkedIn
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
    
    # Production vs Development environment
    if os.environ.get('ENVIRONMENT') == 'production':
        logger.info("🚀 Initializing Chrome WebDriver for Railway.app production environment")
        
        # Railway-specific Chrome binary path
        chrome_binary = os.environ.get('CHROME_BIN', '/usr/bin/google-chrome')
        chrome_options.binary_location = chrome_binary
        
        # Additional production arguments
        chrome_options.add_argument('--single-process')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-log-file')
        chrome_options.add_argument('--disable-permissions-api')
        chrome_options.add_argument('--disable-presentation-api')
        chrome_options.add_argument('--disable-print-preview')
        
        # Use webdriver-manager for automatic ChromeDriver management
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            logger.info("✅ Using webdriver-manager for ChromeDriver")
        except Exception as e:
            logger.warning(f"webdriver-manager failed: {e}, trying fallback")
            # Fallback to manual ChromeDriver path
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
            service = Service(chromedriver_path)
        
    else:
        logger.info("🛠️ Initializing Chrome WebDriver for local development")
        # Local development - use your existing chromedriver
        chromedriver_path = './setup/chromedriver/chromedriver.exe'
        service = Service(chromedriver_path)
    
    try:
        # Create the WebDriver instance
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set timeouts
        driver.implicitly_wait(10)
        driver.set_page_load_timeout(30)
        
        # Execute JavaScript to remove webdriver detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("✅ Chrome WebDriver initialized successfully")
        logger.info(f"🌐 User Agent: {driver.execute_script('return navigator.userAgent')}")
        logger.info(f"📱 Window Size: {driver.get_window_size()}")
        
        return driver
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Chrome WebDriver: {str(e)}")
        raise Exception(f"Could not initialize Chrome WebDriver. Error: {str(e)}")

def test_webdriver():
    """Test the WebDriver configuration"""
    try:
        driver = create_production_chrome_driver()
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        logger.info(f"✅ WebDriver test successful. Page title: {title}")
        return True
    except Exception as e:
        logger.error(f"❌ WebDriver test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the WebDriver configuration
    test_webdriver()