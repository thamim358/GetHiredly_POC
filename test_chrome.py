import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logging.basicConfig(level=logging.INFO)

def test_chrome_setup():
    print("Testing Chrome WebDriver setup...")
    
    # Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Find ChromeDriver
    possible_paths = [
        os.path.join(os.getcwd(), "setup", "chromedriver", "chromedriver.exe"),
        os.path.join(os.path.dirname(__file__), "setup", "chromedriver", "chromedriver.exe"),
        "chromedriver.exe",
        "chromedriver"
    ]
    
    chromedriver_path = None
    for path in possible_paths:
        if os.path.isfile(path):
            chromedriver_path = path
            print(f"Found ChromeDriver at: {path}")
            break
    
    if not chromedriver_path:
        print("ChromeDriver not found! Trying system PATH...")
        try:
            service = Service()
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Failed to start Chrome: {e}")
            return False
    else:
        try:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Failed to start Chrome with path {chromedriver_path}: {e}")
            return False
    
    print("Chrome opened successfully!")
    driver.get("https://www.google.com")
    print(f"Page title: {driver.title}")
    driver.quit()
    print("Chrome closed successfully!")
    return True

if __name__ == "__main__":
    test_chrome_setup()
