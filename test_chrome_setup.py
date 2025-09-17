#!/usr/bin/env python3
"""
Test Chrome Setup - Quick test to verify ChromeDriver works
"""

import sys
import os

# Add current directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("🧪 Testing Chrome Setup...")
    print("=" * 50)
    
    # Test desktop WebDriver manager
    print("\n1. Testing Desktop WebDriver Manager...")
    from desktop_webdriver_manager import DesktopWebDriverManager
    
    manager = DesktopWebDriverManager()
    result = manager.setup_webdriver()
    
    if result and result.get('success'):
        print("✅ Desktop WebDriver Manager: SUCCESS")
        print(f"   Chrome Path: {result['chrome_path']}")
        print(f"   Driver Path: {result['driver_path']}")
        print(f"   Chrome Version: {result['chrome_version']}")
    else:
        print("❌ Desktop WebDriver Manager: FAILED")
        
    # Test Chrome opening (quick test)
    print("\n2. Testing Chrome Opening...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        
        if result and result.get('success'):
            driver_path = result['driver_path']
            options = manager.get_chrome_options()
            
            # Add headless mode for testing
            options.add_argument("--headless=new")
            
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            
            # Test navigation
            driver.get("data:text/html,<html><body><h1>Chrome Test Success!</h1></body></html>")
            title = driver.title
            
            driver.quit()
            
            print("✅ Chrome Opening: SUCCESS")
            print(f"   Test page title: {title}")
        else:
            print("❌ Chrome Opening: SKIPPED (WebDriver setup failed)")
            
    except Exception as e:
        print(f"❌ Chrome Opening: FAILED - {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Chrome setup test completed!")
    
except Exception as e:
    print(f"❌ Test failed with error: {e}")
    import traceback
    traceback.print_exc()

input("\nPress Enter to close...")