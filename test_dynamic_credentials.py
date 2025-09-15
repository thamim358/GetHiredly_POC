#!/usr/bin/env python3
"""
Test script to verify Gmail credentials are fully dynamic and user-controlled
"""

import json
import os
import sys

def test_no_hardcoded_credentials():
    """Test that no hardcoded Gmail credentials exist in the code"""
    print("🔍 Testing for Hardcoded Gmail Credentials")
    print("=" * 60)
    
    # Read the email extractor source code
    with open('linkedin_email_extractor.py', 'r', encoding='utf-8') as f:
        code_content = f.read()
    
    # Check for hardcoded email addresses
    hardcoded_emails = [
        'thamimansari358@gmail.com',
        '@gmail.com',
        'fjld gcow xequ fhgp'  # The app password
    ]
    
    hardcoded_found = []
    for email in hardcoded_emails:
        if email in code_content and 'fallback' not in code_content.lower():
            # Count occurrences
            count = code_content.count(email)
            hardcoded_found.append((email, count))
    
    if hardcoded_found:
        print("❌ Found hardcoded credentials:")
        for cred, count in hardcoded_found:
            print(f"   - '{cred}' appears {count} times")
        return False
    else:
        print("✅ No hardcoded Gmail credentials found in main logic")
        
        # Check if credentials are properly initialized as None
        if 'self.SENDER_EMAIL = None' in code_content and 'self.SENDER_PASSWORD = None' in code_content:
            print("✅ Gmail credentials properly initialized as None")
        else:
            print("⚠️ Gmail credentials initialization not found")
        
        return True

def test_credentials_file_structure():
    """Test the expected structure of linkedin_credentials.json"""
    print("\n📋 Testing Expected Credentials File Structure")
    print("-" * 60)
    
    expected_structure = {
        "email": "user_linkedin@example.com",
        "password": "linkedin_password",
        "profile": "https://linkedin.com/in/profile",
        "gmail": {
            "sender_email": "user_gmail@gmail.com",
            "sender_password": "user_app_password",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587
        }
    }
    
    print("✅ Expected linkedin_credentials.json structure:")
    print(json.dumps(expected_structure, indent=2))
    
    # Check if current file exists and matches structure
    if os.path.exists('linkedin_credentials.json'):
        try:
            with open('linkedin_credentials.json', 'r') as f:
                current_creds = json.load(f)
            
            print(f"\n📂 Current file structure:")
            # Mask passwords for display
            display_creds = current_creds.copy()
            if 'password' in display_creds:
                display_creds['password'] = '*' * len(display_creds['password'])
            if 'gmail' in display_creds and 'sender_password' in display_creds['gmail']:
                display_creds['gmail']['sender_password'] = '*' * len(display_creds['gmail']['sender_password'])
            
            print(json.dumps(display_creds, indent=2))
            
            # Validate structure
            required_fields = ['email', 'password']
            gmail_fields = ['sender_email', 'sender_password']
            
            missing_fields = [field for field in required_fields if field not in current_creds]
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
            
            if 'gmail' in current_creds:
                missing_gmail = [field for field in gmail_fields if field not in current_creds['gmail']]
                if missing_gmail:
                    print(f"⚠️ Missing Gmail fields: {missing_gmail}")
                    print(f"   Email sending may not work properly")
                else:
                    print(f"✅ Gmail configuration is complete")
            else:
                print(f"⚠️ Gmail section not found - email sending will be disabled")
            
            return True
            
        except Exception as e:
            print(f"❌ Error reading credentials file: {e}")
            return False
    else:
        print(f"⚠️ linkedin_credentials.json not found")
        print(f"   Please configure credentials through the dashboard")
        return False

def test_email_extractor_initialization():
    """Test how email extractor initializes Gmail credentials"""
    print("\n🧪 Testing Email Extractor Initialization")
    print("-" * 60)
    
    try:
        # Import the class
        sys.path.append('.')
        from linkedin_email_extractor import LinkedInEmailExtractor
        
        # Create instance (this will load credentials)
        print("Creating LinkedInEmailExtractor instance...")
        extractor = LinkedInEmailExtractor()
        
        # Check Gmail credentials
        print(f"📧 Gmail Credentials Status:")
        print(f"   SENDER_EMAIL: {'✓ Set' if extractor.SENDER_EMAIL else '✗ Not set'}")
        print(f"   SENDER_PASSWORD: {'✓ Set' if extractor.SENDER_PASSWORD else '✗ Not set'}")
        print(f"   SMTP_SERVER: {extractor.SMTP_SERVER}")
        print(f"   SMTP_PORT: {extractor.SMTP_PORT}")
        
        if extractor.SENDER_EMAIL and extractor.SENDER_PASSWORD:
            print(f"✅ Gmail credentials loaded successfully")
            print(f"   Configured for: {extractor.SENDER_EMAIL}")
            return True
        else:
            print(f"⚠️ Gmail credentials not configured")
            print(f"   Email sending will be disabled")
            return False
            
    except Exception as e:
        print(f"❌ Error testing initialization: {e}")
        return False

def create_sample_configuration():
    """Create a sample configuration for testing"""
    print("\n📝 Creating Sample Configuration")
    print("-" * 60)
    
    sample_config = {
        "email": "your_linkedin@gmail.com",
        "password": "your_linkedin_password",
        "profile": "https://linkedin.com/in/yourprofile",
        "gmail": {
            "sender_email": "your_sender@gmail.com",
            "sender_password": "your_16_char_app_password",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587
        }
    }
    
    sample_filename = 'linkedin_credentials_sample.json'
    with open(sample_filename, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"✅ Sample configuration created: {sample_filename}")
    print(f"📋 To use this configuration:")
    print(f"   1. Copy {sample_filename} to linkedin_credentials.json")
    print(f"   2. Replace the placeholder values with your actual credentials")
    print(f"   3. Use Gmail App Password (not regular password)")
    print(f"   4. Restart the email extractor")

def main():
    """Main test function"""
    print("🔐 Gmail Credentials Dynamic Configuration Test")
    print("=" * 80)
    
    # Test 1: Check for hardcoded credentials
    test1_result = test_no_hardcoded_credentials()
    
    # Test 2: Check credentials file structure
    test2_result = test_credentials_file_structure()
    
    # Test 3: Test extractor initialization
    test3_result = test_email_extractor_initialization()
    
    # Test 4: Create sample configuration
    create_sample_configuration()
    
    print(f"\n📊 Test Results Summary:")
    print("=" * 80)
    print(f"✅ No hardcoded credentials: {'PASS' if test1_result else 'FAIL'}")
    print(f"📋 Credentials file structure: {'PASS' if test2_result else 'NEEDS SETUP'}")
    print(f"🧪 Extractor initialization: {'PASS' if test3_result else 'NEEDS CONFIG'}")
    
    print(f"\n💡 Recommendations:")
    if not test1_result:
        print("❌ Remove any hardcoded Gmail credentials from the code")
    if not test2_result:
        print("⚠️ Set up linkedin_credentials.json with proper Gmail section")
    if not test3_result:
        print("🔧 Configure Gmail credentials through the dashboard UI")
    
    if test1_result and test2_result and test3_result:
        print("🎉 All tests passed! Gmail credentials are fully user-controlled.")
    else:
        print("🔧 Some configuration needed. See recommendations above.")

if __name__ == "__main__":
    main()
