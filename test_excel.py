'''
Test script to verify Excel functionality for job applications
'''

import pandas as pd
import os
from datetime import datetime

# Test data
test_data = {
    'Job ID': 'TEST123',
    'Title': 'Software Engineer',
    'Company': 'Test Company',
    'Work Location': 'Remote',
    'Work Style': 'Full-time',
    'About Job': 'Test job description',
    'Experience required': '3 years',
    'Skills required': 'Python, JavaScript',
    'HR Name': 'John Doe',
    'HR Link': 'https://linkedin.com/in/johndoe',
    'HR Email': 'john.doe@testcompany.com',
    'Resume': 'default_resume.pdf',
    'Re-posted': False,
    'Date Posted': datetime.now(),
    'Date Applied': datetime.now(),
    'Job Link': 'https://linkedin.com/jobs/test123',
    'External Job link': 'https://company.com/jobs/test',
    'Questions Found': 'None',
    'Connect Request': 'Not sent'
}

# Test file name
test_file = "test_applications.xlsx"

def test_excel_functionality():
    try:
        # Test creating new file
        df = pd.DataFrame([test_data])
        df.to_excel(test_file, index=False)
        print("✅ Created new Excel file successfully")
        
        # Test appending to existing file
        test_data2 = test_data.copy()
        test_data2['Job ID'] = 'TEST456'
        test_data2['Title'] = 'Data Scientist'
        
        df_existing = pd.read_excel(test_file)
        df_new = pd.DataFrame([test_data2])
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_excel(test_file, index=False)
        print("✅ Appended to existing Excel file successfully")
        
        # Verify data
        df_final = pd.read_excel(test_file)
        print(f"✅ Final file has {len(df_final)} rows")
        print("\nColumns in Excel file:")
        for col in df_final.columns:
            print(f"  - {col}")
        
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
            print("✅ Cleaned up test file")
            
        print("\n🎉 All Excel functionality tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        # Cleanup on error
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_excel_functionality()
