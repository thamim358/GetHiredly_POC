#!/usr/bin/env python3
"""
Simple Chrome Test for Executable
This script tests if Chrome opens visibly when run as an executable
"""

import sys
import time

def test_chrome_visibility():
    print("🧪 Testing Chrome visibility in executable mode...")
    
    # Check if running as executable
    is_executable = getattr(sys, 'frozen', False)
    print(f"📋 Running as executable: {is_executable}")
    print(f"📂 sys.executable: {sys.executable}")
    
    try:
        import undetected_chromedriver as uc
        print("✅ Undetected-chromedriver imported successfully")
        
        # Create Chrome options
        options = uc.ChromeOptions()
        
        if is_executable:
            print("🔧 Executable mode: Adding visibility options")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("detach", True)
        else:
            print("🔧 Script mode: Using standard options")
            options.add_argument("--start-maximized")
        
        print("🚀 Starting Chrome...")
        driver = uc.Chrome(options=options)
        
        print("✅ Chrome started successfully!")
        print("🌐 Navigating to test page...")
        
        driver.get("https://www.google.com")
        print("✅ Navigation successful!")
        
        print("⏳ Waiting 10 seconds for you to see the Chrome window...")
        time.sleep(10)
        
        print("🔄 Closing Chrome...")
        driver.quit()
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chrome_visibility()
    input("Press Enter to exit...")