#!/usr/bin/env python3
"""
Railway Deployment Validation Script
Checks if all files are ready for deployment
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists and report status"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ Missing {description}: {filepath}")
        return False

def validate_deployment():
    """Validate all deployment files are present"""
    print("🔍 Validating Railway.app deployment files...\n")
    
    all_good = True
    
    # Check essential deployment files
    files_to_check = [
        ("Dockerfile", "Docker configuration"),
        ("railway.toml", "Railway configuration"),
        ("requirements.txt", "Python dependencies"),
        ("production_webdriver.py", "Production WebDriver"),
        (".dockerignore", "Docker ignore file"),
        ("professional_dashboard_api.py", "Main Flask application")
    ]
    
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_good = False
    
    print()
    
    # Check requirements.txt content
    if os.path.exists("requirements.txt"):
        try:
            with open("requirements.txt", 'r', encoding='utf-8') as f:
                content = f.read()
                if "Flask==" in content:
                    print("✅ Flask found in requirements.txt")
                else:
                    print("⚠️  Flask not found in requirements.txt")
                    all_good = False
                    
                if "selenium==" in content:
                    print("✅ Selenium found in requirements.txt")
                else:
                    print("⚠️  Selenium not found in requirements.txt")
                    all_good = False
        except UnicodeDecodeError:
            print("⚠️  Encoding issue with requirements.txt - trying alternative encoding")
            try:
                with open("requirements.txt", 'r', encoding='cp1252') as f:
                    content = f.read()
                    if "Flask" in content and "selenium" in content:
                        print("✅ Flask and Selenium found in requirements.txt")
                    else:
                        print("⚠️  Missing dependencies in requirements.txt")
                        all_good = False
            except Exception as e:
                print(f"❌ Could not read requirements.txt: {e}")
                all_good = False
    
    print()
    
    # Check if professional_dashboard_api.py has production config
    if os.path.exists("professional_dashboard_api.py"):
        try:
            with open("professional_dashboard_api.py", 'r', encoding='utf-8') as f:
                content = f.read()
                if "ENVIRONMENT = os.environ.get('ENVIRONMENT'" in content:
                    print("✅ Production configuration found in Flask app")
                else:
                    print("⚠️  Production configuration missing in Flask app")
                    all_good = False
                    
                if "/health" in content:
                    print("✅ Health check endpoint found")
                else:
                    print("⚠️  Health check endpoint missing")
                    all_good = False
        except UnicodeDecodeError:
            print("⚠️  Encoding issue with Flask app - checking basics")
            if os.path.getsize("professional_dashboard_api.py") > 1000:
                print("✅ Flask app file exists and has content")
            else:
                print("❌ Flask app file seems too small")
                all_good = False
    
    print()
    
    if all_good:
        print("🎉 All deployment files are ready!")
        print("\n📋 Next steps:")
        print("1. git add .")
        print("2. git commit -m 'Fix Railway deployment with Docker'")
        print("3. git push origin main")
        print("4. Deploy on Railway.app")
        print("\n🌐 Your app will be live at: https://your-app.railway.app")
    else:
        print("❌ Some files are missing or incomplete.")
        print("Please check the errors above and fix them before deploying.")
    
    return all_good

if __name__ == "__main__":
    validate_deployment()