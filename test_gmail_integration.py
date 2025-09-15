#!/usr/bin/env python3
"""
Test script to verify Gmail credentials handling in the dashboard
"""

import json
import requests
import os
import time

def test_gmail_credentials_ui():
    """Test the complete flow of Gmail credentials from UI to backend to file"""
    print("🧪 Testing Gmail Credentials Flow")
    print("=" * 60)
    
    # Sample user data with Gmail credentials (as would come from the UI)
    test_user_data = {
        "personal": {
            "fullName": "Thamim Ansari",
            "email": "thamim@example.com",
            "phone": "+1234567890",
            "location": "India",
            "website": "https://linkedin.com/in/thamim358"
        },
        "linkedin": {
            "email": "thamimansari358@gmail.com",
            "password": "THAMIMansari$1",
            "profile": "https://linkedin.com/in/thamim358",
            "gmail": {
                "senderEmail": "thamimansari358@gmail.com",
                "senderPassword": "fjld gcow xequ fhgp"
            }
        },
        "job": {
            "role": "React Developer",
            "customTitle": "",
            "subject": "Application for React.js Developer Position",
            "searchTerms": ["React js Developer", "Frontend Developer"],
            "emailTemplate": "<p>Dear Hiring Manager,</p><p>I am interested in the position...</p>",
            "botType": "email-extractor",
            "dateFilter": "past-week",
            "companyFilter": {
                "enabled": True,
                "companies": [{"name": "Google", "enabled": True}, {"name": "Microsoft", "enabled": True}]
            },
            "countryFilter": {
                "enabled": True,
                "countries": [{"name": "UAE", "searchTerms": "UAE", "enabled": True}]
            }
        }
    }
    
    print("📝 Test Data Prepared:")
    print(f"   LinkedIn Email: {test_user_data['linkedin']['email']}")
    print(f"   Gmail Sender: {test_user_data['linkedin']['gmail']['senderEmail']}")
    print(f"   Gmail Password: {'*' * len(test_user_data['linkedin']['gmail']['senderPassword'])}")
    
    return test_user_data

def test_credentials_file_format():
    """Test that credentials are saved in the correct format"""
    print("\n📂 Testing LinkedIn Credentials File Format")
    print("-" * 60)
    
    if os.path.exists('linkedin_credentials.json'):
        try:
            with open('linkedin_credentials.json', 'r') as f:
                credentials = json.load(f)
            
            print("✅ LinkedIn credentials file found and loaded")
            
            # Check required LinkedIn fields
            required_linkedin = ['email', 'password']
            for field in required_linkedin:
                if field in credentials:
                    print(f"   ✅ LinkedIn {field}: Present")
                else:
                    print(f"   ❌ LinkedIn {field}: Missing")
            
            # Check Gmail configuration
            if 'gmail' in credentials:
                print(f"   ✅ Gmail configuration: Present")
                gmail_config = credentials['gmail']
                
                gmail_fields = ['sender_email', 'sender_password', 'smtp_server', 'smtp_port']
                for field in gmail_fields:
                    if field in gmail_config:
                        if field == 'sender_password':
                            print(f"   ✅ Gmail {field}: Present ({'*' * len(str(gmail_config[field]))})")
                        else:
                            print(f"   ✅ Gmail {field}: {gmail_config[field]}")
                    else:
                        print(f"   ⚠️ Gmail {field}: Missing (using default)")
            else:
                print(f"   ⚠️ Gmail configuration: Missing")
            
            return credentials
            
        except json.JSONDecodeError as e:
            print(f"   ❌ Error parsing JSON: {e}")
            return None
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            return None
    else:
        print("   ⚠️ LinkedIn credentials file not found")
        return None

def simulate_email_extractor_loading():
    """Simulate how the email extractor loads Gmail credentials"""
    print("\n🔄 Simulating Email Extractor Gmail Loading")
    print("-" * 60)
    
    # Default values (as in the email extractor)
    SENDER_EMAIL = "default@gmail.com"
    SENDER_PASSWORD = "default_password"
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    try:
        if os.path.exists('linkedin_credentials.json'):
            with open('linkedin_credentials.json', 'r') as f:
                linkedin_creds = json.load(f)
            
            print(f"📧 LinkedIn Email: {linkedin_creds.get('email', 'Not found')}")
            
            # Load Gmail credentials from the same file
            if 'gmail' in linkedin_creds:
                gmail_config = linkedin_creds['gmail']
                SENDER_EMAIL = gmail_config.get('sender_email', SENDER_EMAIL)
                SENDER_PASSWORD = gmail_config.get('sender_password', SENDER_PASSWORD)
                SMTP_SERVER = gmail_config.get('smtp_server', SMTP_SERVER)
                SMTP_PORT = gmail_config.get('smtp_port', SMTP_PORT)
                print(f"✅ Gmail credentials loaded from linkedin_credentials.json")
            else:
                print(f"⚠️ Using default Gmail credentials (no gmail section found)")
                
        else:
            print(f"⚠️ Using default Gmail credentials (no linkedin_credentials.json found)")
            
        print(f"\n📤 Final Email Configuration (as loaded by email extractor):")
        print(f"   Sender Email: {SENDER_EMAIL}")
        print(f"   Sender Password: {'*' * len(SENDER_PASSWORD)}")
        print(f"   SMTP Server: {SMTP_SERVER}")
        print(f"   SMTP Port: {SMTP_PORT}")
        
        return {
            'sender_email': SENDER_EMAIL,
            'sender_password': SENDER_PASSWORD,
            'smtp_server': SMTP_SERVER,
            'smtp_port': SMTP_PORT
        }
        
    except Exception as e:
        print(f"❌ Error in simulation: {e}")
        return None

def test_ui_local_storage_simulation():
    """Simulate local storage behavior for Gmail credentials"""
    print("\n💾 Testing UI Local Storage Simulation")
    print("-" * 60)
    
    # Simulate what would be saved to localStorage
    ui_data = {
        'linkedinEmail': 'thamimansari358@gmail.com',
        'linkedinPassword': 'THAMIMansari$1',
        'linkedinProfile': 'https://linkedin.com/in/thamim358',
        'senderEmail': 'thamimansari358@gmail.com',
        'senderPassword': 'fjld gcow xequ fhgp'
    }
    
    print("📱 UI Local Storage Data (simulated):")
    for key, value in ui_data.items():
        if 'password' in key.lower():
            print(f"   {key}: {'*' * len(value)}")
        else:
            print(f"   {key}: {value}")
    
    # Simulate how collectUserData() would structure this for the API
    api_data = {
        "linkedin": {
            "email": ui_data['linkedinEmail'],
            "password": ui_data['linkedinPassword'],
            "profile": ui_data['linkedinProfile'],
            "gmail": {
                "senderEmail": ui_data['senderEmail'],
                "senderPassword": ui_data['senderPassword']
            }
        }
    }
    
    print(f"\n🔄 API Data Structure (from collectUserData()):")
    print(json.dumps(api_data, indent=2))
    
    return api_data

def main():
    """Main test function"""
    print("🔧 Gmail Credentials Integration Test")
    print("=" * 80)
    
    # Test 1: Prepare test data
    test_data = test_gmail_credentials_ui()
    
    # Test 2: Check current credentials file format
    current_creds = test_credentials_file_format()
    
    # Test 3: Simulate email extractor loading
    extractor_config = simulate_email_extractor_loading()
    
    # Test 4: Simulate UI local storage
    ui_simulation = test_ui_local_storage_simulation()
    
    print(f"\n📋 Test Summary:")
    print("-" * 80)
    print(f"✅ Test data prepared with Gmail credentials")
    print(f"{'✅' if current_creds else '⚠️'} LinkedIn credentials file {'found' if current_creds else 'not found'}")
    print(f"{'✅' if current_creds and 'gmail' in current_creds else '⚠️'} Gmail configuration {'present' if current_creds and 'gmail' in current_creds else 'missing'}")
    print(f"{'✅' if extractor_config else '❌'} Email extractor simulation {'successful' if extractor_config else 'failed'}")
    print(f"✅ UI local storage simulation completed")
    
    print(f"\n💡 Next Steps:")
    print("1. ✅ Gmail fields added to UI credentials tab")
    print("2. ✅ Local storage save/load functions updated")
    print("3. ✅ Backend validation for Gmail credentials added")
    print("4. ✅ Email extractor updated to load Gmail credentials")
    print("5. 🔄 Test the complete flow by:")
    print("   - Starting the dashboard server")
    print("   - Fill in Gmail credentials in the UI")
    print("   - Start email extractor")
    print("   - Verify credentials are loaded correctly")

if __name__ == "__main__":
    main()
