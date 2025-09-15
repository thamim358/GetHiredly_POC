#!/usr/bin/env python3
"""
Quick test to verify Gmail credentials loading
"""

import json
import os

def test_credentials_loading():
    print("🔍 Testing Gmail Credentials Loading")
    print("=" * 50)
    
    # Check if credentials file exists
    if not os.path.exists('linkedin_credentials.json'):
        print("❌ linkedin_credentials.json not found")
        return False
    
    # Load credentials
    with open('linkedin_credentials.json', 'r') as f:
        creds = json.load(f)
    
    print("📂 Current credentials structure:")
    # Mask passwords for display
    display_creds = creds.copy()
    if 'password' in display_creds:
        display_creds['password'] = '*' * 10
    if 'gmail' in display_creds:
        gmail_copy = display_creds['gmail'].copy()
        if 'senderPassword' in gmail_copy:
            gmail_copy['senderPassword'] = '*' * 10
        if 'sender_password' in gmail_copy:
            gmail_copy['sender_password'] = '*' * 10
        display_creds['gmail'] = gmail_copy
    
    print(json.dumps(display_creds, indent=2))
    
    # Test the loading logic (same as in email extractor)
    if 'gmail' in creds:
        gmail_config = creds['gmail']
        
        # Handle both UI format (camelCase) and backend format (snake_case)
        sender_email = (gmail_config.get('senderEmail') or 
                       gmail_config.get('sender_email'))
        sender_password = (gmail_config.get('senderPassword') or 
                          gmail_config.get('sender_password'))
        
        print(f"\n📧 Gmail Credentials Test:")
        print(f"   Available keys: {list(gmail_config.keys())}")
        print(f"   SENDER_EMAIL: {'✓ ' + sender_email if sender_email else '✗ Not found'}")
        print(f"   SENDER_PASSWORD: {'✓ Set' if sender_password else '✗ Not found'}")
        
        if sender_email and sender_password:
            print(f"✅ Gmail credentials loaded successfully!")
            return True
        else:
            print(f"❌ Gmail credentials incomplete")
            return False
    else:
        print(f"❌ No Gmail section found")
        return False

if __name__ == "__main__":
    success = test_credentials_loading()
    if success:
        print(f"\n🎉 Gmail credentials are properly configured!")
        print(f"The email extractor should now be able to send emails.")
    else:
        print(f"\n🔧 Please check your Gmail configuration in the dashboard.")
