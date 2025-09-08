#!/usr/bin/env python3
"""
Test script for continuous scrolling functionality
"""

import logging
from linkedin_email_extractor import LinkedInEmailExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_continuous_scrolling():
    """Test the continuous scrolling without full email sending"""
    
    print("="*60)
    print("TESTING CONTINUOUS SCROLLING")
    print("="*60)
    print("This test will:")
    print("1. Login to LinkedIn")
    print("2. Search for React Developer posts")
    print("3. Continuously scroll and process posts")
    print("4. Extract emails (but not send them)")
    print("5. Show statistics")
    print("="*60)
    
    # Create extractor instance
    extractor = LinkedInEmailExtractor()
    
    # Temporarily disable email sending for testing
    original_send_email = extractor.send_email
    def mock_send_email(email):
        logging.info(f"[TEST MODE] Would send email to: {email}")
        extractor.emails_sent += 1
        extractor.sent_emails.add(email.lower())
        return True
    
    extractor.send_email = mock_send_email
    
    try:
        # Setup WebDriver
        extractor.setup_driver()
        
        # Login to LinkedIn
        extractor.login_to_linkedin()
        
        # Use the first search term
        search_term = extractor.search_terms[0] if extractor.search_terms else "React Developer"
        logging.info(f"Testing with search term: {search_term}")
        
        if extractor.search_posts(search_term):
            logging.info("Starting continuous extraction (test mode)...")
            extractor.extract_emails_from_posts_continuously()
        
        # Print test results
        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)
        print(f"Posts processed: {extractor.posts_processed}")
        print(f"Emails found: {len(extractor.extracted_emails)}")
        print(f"Emails that would be sent: {extractor.emails_sent}")
        if extractor.extracted_emails:
            print("Found emails:", list(extractor.extracted_emails))
        print("="*60)
        
    except Exception as e:
        logging.error(f"Test failed: {e}")
    finally:
        if extractor.driver:
            try:
                input("Press Enter to close browser...")
                extractor.driver.quit()
            except:
                pass

if __name__ == "__main__":
    test_continuous_scrolling()
