#!/usr/bin/env python3
"""
Test script to verify job role configuration is working
"""

import json
import os

# Test configuration
test_config = {
    "subject": "Application for UI Developer / Frontend UI Developer – 3+ Years Experience",
    "search_terms": ["UI Developer", "UI/UX Developer", "User Interface Developer", "Frontend UI Developer", "Web UI Developer", "UI Engineer"],
    "resume_file": "Thamim_Ansari_UI_developer1.pdf",
    "email_body": "<html><body><p>Test UI Developer email body</p></body></html>"
}

# Write test configuration
with open('temp_job_config.json', 'w') as f:
    json.dump(test_config, f, indent=2)

print("✅ Test configuration written to temp_job_config.json")
print(f"📧 Subject: {test_config['subject']}")
print(f"🔍 Search Terms: {test_config['search_terms']}")
print(f"📎 Resume: {test_config['resume_file']}")

# Test if the linkedin_email_extractor can load it
try:
    from linkedin_email_extractor import LinkedInEmailExtractor
    
    extractor = LinkedInEmailExtractor()
    
    print(f"\n🎯 After loading configuration:")
    print(f"📧 Email Subject: {extractor.SUBJECT}")
    print(f"🔍 Search Terms: {extractor.search_terms}")
    print(f"📎 Resume File: {extractor.ATTACHMENT_PATH}")
    
    if extractor.search_terms == test_config['search_terms']:
        print("✅ Search terms loaded correctly!")
    else:
        print("❌ Search terms not loaded correctly")
        
    if extractor.ATTACHMENT_PATH == test_config['resume_file']:
        print("✅ Resume file loaded correctly!")
    else:
        print("❌ Resume file not loaded correctly")
        
except Exception as e:
    print(f"❌ Error testing configuration: {e}")

# Clean up
if os.path.exists('temp_job_config.json'):
    os.remove('temp_job_config.json')
    print("\n🧹 Cleaned up test file")
