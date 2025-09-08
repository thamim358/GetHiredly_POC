'''
Email Job Applier - LinkedIn Job Email Extractor and Sender
Author:     Thamim ansari
LinkedIn:   https://www.linkedin.com/in/thamim358/

This script searches for jobs on LinkedIn, extracts emails from job posts,
and sends personalized job applications via email.

Version:    1.0.0
'''

import os
import csv
import re
import time
import json
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Set

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Import existing modules
from config.personals import current_city
from config.questions import *
from config.search import search_terms, date_posted, experience_level, job_type, on_site
from config.secrets import username, password
from config.settings import *

from modules.open_chrome import *
from modules.helpers import *
from modules.clickers_and_finders import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_job_applier.log'),
        logging.StreamHandler()
    ]
)

class EmailJobApplier:
    def __init__(self):
        # Email configuration
        self.SMTP_SERVER = "smtp.gmail.com"
        self.SMTP_PORT = 587
        self.SENDER_EMAIL = "thamimansari358@gmail.com"
        self.SENDER_PASSWORD = "fjld gcow xequ fhgp"
        
        # Email template
        self.SUBJECT = "Application for React.js Developer / Frontend Developer – 3+ Years Experience"
        self.BODY_HTML = """
        <html>
        <body>
            <p>Dear Hiring Manager,</p>
            
            <p>I hope you're doing well.</p>
            
            <p>I am writing to express my interest in the <strong>React.js Developer</strong> or <strong>Frontend Developer</strong> position. With <strong>3+ years of experience</strong> in building responsive and user-friendly web applications, I am excited about the opportunity to contribute to your development team.</p>
            
            <p><strong>Key Skills & Experience:</strong></p>
            <ul>
                <li>Proficient in <strong>React.js</strong>, <strong>JavaScript (ES6+)</strong>, <strong>TypeScript</strong>, <strong>HTML5</strong>, <strong>CSS3</strong>, and <strong>Tailwind CSS</strong></li>
                <li>Expertise in <strong>RESTful API integration</strong>, <strong>state management (Redux, Context API)</strong>, and <strong>responsive UI/UX</strong> development</li>
                <li>Familiar with <strong>Git</strong>, <strong>Webpack</strong>, <strong>Vite</strong>, <strong>Postman</strong>, <strong>Figma</strong>, and <strong>Adobe XD</strong></li>
                <li>Passionate about <strong>clean code</strong>, <strong>performance optimization</strong>, <strong>cross-browser compatibility</strong>, and creating intuitive user experiences</li>
            </ul>
            
            <p>I have attached my updated resume for your review. I would be grateful for the opportunity to discuss how my background aligns with your team's needs. I am an <strong>immediate joiner</strong>, highly adaptable, and eager to contribute to a fast-paced and growth-driven environment.</p>
            
            <p>Thank you for your time and consideration. I look forward to hearing from you.</p>
            
            <p>Best regards,<br>
            <strong>Thamim Ansari</strong><br>
            thamimansari358@gmail.com<br>
            +91 8072098022<br>
            <a href="https://github.com/thamim358">https://github.com/thamim358</a></p>
        </body>
        </html>
        """
        
        self.ATTACHMENT_PATH = "Thamim_Ansari_Resume.pdf"
        
        # Statistics
        self.emails_extracted = 0
        self.emails_sent = 0
        self.emails_failed = 0
        self.jobs_processed = 0
        
        # Email patterns for extraction
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,}'
        ]
        
        # Store extracted emails to avoid duplicates
        self.extracted_emails: Set[str] = set()
        self.sent_emails: Set[str] = set()
        
    def is_logged_in_LN(self) -> bool:
        """Check if user is logged-in in LinkedIn"""
        if driver.current_url == "https://www.linkedin.com/feed/": 
            return True
        if try_linkText(driver, "Sign in"): 
            return False
        if try_xp(driver, '//button[@type="submit" and contains(text(), "Sign in")]'):  
            return False
        if try_linkText(driver, "Join now"): 
            return False
        print_lg("Didn't find Sign in link, so assuming user is logged in!")
        return True

    def login_LN(self) -> None:
        """Login to LinkedIn"""
        driver.get("https://www.linkedin.com/login")
        try:
            wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?")))
            try:
                text_input_by_ID(driver, "username", username, 1)
            except Exception as e:
                print_lg("Couldn't find username field.")
            try:
                text_input_by_ID(driver, "password", password, 1)
            except Exception as e:
                print_lg("Couldn't find password field.")
            
            driver.find_element(By.XPATH, '//button[@type="submit" and contains(text(), "Sign in")]').click()
        except Exception as e1:
            try:
                profile_button = find_by_class(driver, "profile__details")
                profile_button.click()
            except Exception as e2:
                print_lg("Couldn't Login!")

        try:
            wait.until(EC.url_to_be("https://www.linkedin.com/feed/"))
            return print_lg("Login successful!")
        except Exception as e:
            print_lg("Login might have failed!")

    def set_search_location(self) -> None:
        """Set search location based on config"""
        try:
            location_field = driver.find_element(By.XPATH, "//input[contains(@id, 'jobs-search-box-location-id')]")
            location_field.clear()
            location_field.send_keys(current_city)
            buffer(2)
            try:
                first_suggestion = driver.find_element(By.XPATH, "//div[@data-test-suggestion-index='0']")
                first_suggestion.click()
            except:
                location_field.send_keys(Keys.ENTER)
            print_lg(f"Location set to: {current_city}")
        except Exception as e:
            print_lg("Failed to set location:", e)

    def apply_filters(self) -> None:
        """Apply search filters"""
        try:
            # Open filters
            filter_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'filter') or contains(text(), 'filter')]"))
            )
            filter_button.click()
            buffer(2)
            
            # Apply date posted filter
            if date_posted != "Any time":
                try:
                    date_filter = driver.find_element(By.XPATH, f"//label[contains(text(), '{date_posted}')]")
                    date_filter.click()
                    print_lg(f"Applied date filter: {date_posted}")
                except:
                    print_lg(f"Could not apply date filter: {date_posted}")
            
            # Apply experience level filter
            if experience_level:
                for level in experience_level:
                    try:
                        exp_filter = driver.find_element(By.XPATH, f"//label[contains(text(), '{level}')]")
                        exp_filter.click()
                        print_lg(f"Applied experience filter: {level}")
                    except:
                        print_lg(f"Could not apply experience filter: {level}")
            
            # Apply job type filter
            if job_type:
                for jtype in job_type:
                    try:
                        job_type_filter = driver.find_element(By.XPATH, f"//label[contains(text(), '{jtype}')]")
                        job_type_filter.click()
                        print_lg(f"Applied job type filter: {jtype}")
                    except:
                        print_lg(f"Could not apply job type filter: {jtype}")
            
            # Apply location filter (using on_site instead of work_location_type)
            if on_site:
                for loc_type in on_site:
                    try:
                        location_filter = driver.find_element(By.XPATH, f"//label[contains(text(), '{loc_type}')]")
                        location_filter.click()
                        print_lg(f"Applied location filter: {loc_type}")
                    except:
                        print_lg(f"Could not apply location filter: {loc_type}")
            
            # Apply filters button
            try:
                apply_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Apply') or contains(text(), 'Show results')]")
                apply_button.click()
                buffer(3)
                print_lg("Filters applied successfully!")
            except:
                print_lg("Could not find apply filters button")
                
        except Exception as e:
            print_lg("Failed to apply filters:", e)

    def extract_emails_from_text(self, text: str) -> List[str]:
        """Extract email addresses from text using regex patterns"""
        emails = []
        for pattern in self.email_patterns:
            found_emails = re.findall(pattern, text, re.IGNORECASE)
            emails.extend(found_emails)
        
        # Clean and validate emails
        cleaned_emails = []
        for email in emails:
            email = email.strip().lower()
            # Basic validation
            if '@' in email and '.' in email.split('@')[1]:
                # Avoid common false positives
                if not any(invalid in email for invalid in ['noreply', 'no-reply', 'donotreply', 'example.com', 'test.com']):
                    cleaned_emails.append(email)
        
        return list(set(cleaned_emails))  # Remove duplicates

    def extract_emails_from_job_post(self, job_id: str) -> List[str]:
        """Extract emails from a specific job post"""
        emails = []
        try:
            # Click on the job to view details
            job_element = driver.find_element(By.XPATH, f"//li[@data-occludable-job-id='{job_id}']")
            job_element.click()
            buffer(2)
            
            # Wait for job details to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-search__job-details"))
            )
            
            # Extract text from job description
            try:
                job_description = driver.find_element(By.CLASS_NAME, "jobs-search__job-details").text
                emails.extend(self.extract_emails_from_text(job_description))
            except:
                pass
            
            # Try to find "Show more" or "See more" button and click it
            try:
                show_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Show more') or contains(text(), 'See more')]")
                show_more_button.click()
                buffer(2)
                
                # Extract emails from expanded description
                expanded_description = driver.find_element(By.CLASS_NAME, "jobs-search__job-details").text
                emails.extend(self.extract_emails_from_text(expanded_description))
            except:
                pass
            
            # Try to extract from company about section
            try:
                company_about = driver.find_element(By.XPATH, "//section[contains(@class, 'jobs-company')]").text
                emails.extend(self.extract_emails_from_text(company_about))
            except:
                pass
            
            # Try to click on company name to get more details
            try:
                company_link = driver.find_element(By.XPATH, "//a[contains(@class, 'jobs-unified-top-card__company-name')]")
                original_window = driver.current_window_handle
                
                # Open company page in new tab
                driver.execute_script("arguments[0].click();", company_link)
                
                # Switch to new tab if opened
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    buffer(3)
                    
                    # Extract emails from company page
                    try:
                        company_page_text = driver.find_element(By.TAG_NAME, "body").text
                        emails.extend(self.extract_emails_from_text(company_page_text))
                    except:
                        pass
                    
                    # Close company tab and switch back
                    driver.close()
                    driver.switch_to.window(original_window)
            except:
                pass
                
        except Exception as e:
            print_lg(f"Error extracting emails from job {job_id}: {e}")
        
        # Remove duplicates and return
        unique_emails = list(set(emails))
        if unique_emails:
            print_lg(f"Extracted {len(unique_emails)} emails from job {job_id}: {unique_emails}")
        
        return unique_emails

    def create_email_message(self, to_email: str) -> MIMEMultipart:
        """Create email message with attachment"""
        msg = MIMEMultipart()
        msg['From'] = self.SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = self.SUBJECT
        
        # Add body to email
        msg.attach(MIMEText(self.BODY_HTML, 'html'))
        
        # Add attachment if exists
        if os.path.isfile(self.ATTACHMENT_PATH):
            with open(self.ATTACHMENT_PATH, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(self.ATTACHMENT_PATH)}'
            )
            msg.attach(part)
        else:
            print_lg(f"Warning: Resume file {self.ATTACHMENT_PATH} not found!")
        
        return msg

    def send_email(self, to_email: str) -> bool:
        """Send email to a specific address"""
        try:
            if to_email in self.sent_emails:
                print_lg(f"Email already sent to {to_email}, skipping...")
                return False
                
            msg = self.create_email_message(to_email)
            
            # Create SMTP session
            server = smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT)
            server.starttls()
            server.login(self.SENDER_EMAIL, self.SENDER_PASSWORD)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.SENDER_EMAIL, to_email, text)
            server.quit()
            
            self.emails_sent += 1
            self.sent_emails.add(to_email)
            print_lg(f"✓ Email sent successfully to {to_email}")
            logging.info(f"Email sent to {to_email}")
            
            # Save sent email to file
            self.save_sent_email(to_email)
            
            return True
            
        except Exception as e:
            self.emails_failed += 1
            print_lg(f"✗ Failed to send email to {to_email}: {str(e)}")
            logging.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def save_sent_email(self, email: str) -> None:
        """Save sent email to CSV for tracking"""
        try:
            file_path = "sent_emails_log.csv"
            file_exists = os.path.isfile(file_path)
            
            with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['email', 'date_sent', 'subject']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow({
                    'email': email,
                    'date_sent': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'subject': self.SUBJECT
                })
        except Exception as e:
            print_lg(f"Failed to save sent email log: {e}")

    def save_extracted_emails(self, emails: List[str]) -> None:
        """Save extracted emails to JSON file"""
        try:
            file_path = "extracted_emails.json"
            
            # Load existing emails if file exists
            existing_emails = set()
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        existing_emails = set(data.get('emails', []))
                except:
                    pass
            
            # Add new emails
            all_emails = existing_emails.union(set(emails))
            
            # Save updated list
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'emails': list(all_emails),
                    'total_count': len(all_emails),
                    'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
                
            print_lg(f"Saved {len(all_emails)} total emails to {file_path}")
            
        except Exception as e:
            print_lg(f"Failed to save extracted emails: {e}")

    def search_jobs_and_extract_emails(self, search_terms: List[str]) -> None:
        """Main function to search jobs and extract emails"""
        print_lg("Starting job search and email extraction...")
        
        for search_term in search_terms:
            print_lg(f"\n{'='*80}")
            print_lg(f"Searching for: {search_term}")
            print_lg(f"{'='*80}")
            
            # Navigate to LinkedIn jobs search
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={search_term}"
            driver.get(search_url)
            buffer(3)
            
            # Set location
            self.set_search_location()
            
            # Apply filters
            self.apply_filters()
            
            page_count = 0
            max_pages = 5  # Limit to first 5 pages
            
            while page_count < max_pages:
                try:
                    # Wait for job listings to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//li[@data-occludable-job-id]"))
                    )
                    
                    # Get all job listings on current page
                    job_listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")
                    print_lg(f"Found {len(job_listings)} jobs on page {page_count + 1}")
                    
                    # Process each job
                    for job in job_listings:
                        try:
                            job_id = job.get_attribute("data-occludable-job-id")
                            if not job_id:
                                continue
                                
                            self.jobs_processed += 1
                            print_lg(f"\nProcessing job {self.jobs_processed}: {job_id}")
                            
                            # Extract emails from this job
                            job_emails = self.extract_emails_from_job_post(job_id)
                            
                            if job_emails:
                                self.extracted_emails.update(job_emails)
                                self.emails_extracted += len(job_emails)
                                
                                # Send emails immediately
                                for email in job_emails:
                                    if email not in self.sent_emails:
                                        success = self.send_email(email)
                                        if success:
                                            time.sleep(2)  # Delay between emails
                                
                                # Save extracted emails
                                self.save_extracted_emails(job_emails)
                            
                            # Small delay between jobs
                            time.sleep(1)
                            
                        except Exception as e:
                            print_lg(f"Error processing job: {e}")
                            continue
                    
                    # Try to go to next page
                    try:
                        next_button = driver.find_element(By.XPATH, "//button[@aria-label='Next' or contains(@class, 'artdeco-pagination__button--next')]")
                        if next_button.is_enabled():
                            next_button.click()
                            buffer(3)
                            page_count += 1
                        else:
                            print_lg("No more pages available")
                            break
                    except:
                        print_lg("Could not find next page button")
                        break
                        
                except Exception as e:
                    print_lg(f"Error on page {page_count + 1}: {e}")
                    break
            
            print_lg(f"Completed search for: {search_term}")
            print_lg(f"Jobs processed: {self.jobs_processed}")
            print_lg(f"Emails extracted: {len(self.extracted_emails)}")
            print_lg(f"Emails sent: {self.emails_sent}")

    def get_statistics(self) -> dict:
        """Get statistics of the email extraction and sending process"""
        return {
            'jobs_processed': self.jobs_processed,
            'emails_extracted': len(self.extracted_emails),
            'emails_sent': self.emails_sent,
            'emails_failed': self.emails_failed,
            'unique_emails': list(self.extracted_emails)
        }

    def run(self):
        """Main execution function"""
        try:
            print_lg("Starting Email Job Applier...")
            
            # Login to LinkedIn
            print_lg("Attempting to login to LinkedIn...")
            driver.get("https://www.linkedin.com/login")
            
            if not self.is_logged_in_LN():
                print_lg("Not logged in, attempting login...")
                self.login_LN()
            else:
                print_lg("Already logged in to LinkedIn!")
            
            # Search terms from config
            search_keywords = search_terms
            
            # Start the job search and email extraction process
            self.search_jobs_and_extract_emails(search_keywords)
            
            # Print final statistics
            stats = self.get_statistics()
            print_lg("\n" + "="*80)
            print_lg("FINAL STATISTICS")
            print_lg("="*80)
            print_lg(f"Jobs processed: {stats['jobs_processed']}")
            print_lg(f"Unique emails extracted: {stats['emails_extracted']}")
            print_lg(f"Emails sent successfully: {stats['emails_sent']}")
            print_lg(f"Emails failed: {stats['emails_failed']}")
            print_lg(f"Success rate: {(stats['emails_sent'] / max(stats['emails_extracted'], 1)) * 100:.1f}%")
            print_lg("="*80)
            
            # Save final statistics
            with open('email_applier_stats.json', 'w') as f:
                json.dump({
                    **stats,
                    'completion_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
            
        except Exception as e:
            print_lg(f"Critical error in email job applier: {e}")
            logging.error(f"Critical error: {e}")
        finally:
            try:
                if driver:
                    driver.quit()
            except:
                pass

def main():
    """Main function"""
    try:
        # Initialize the email job applier
        email_applier = EmailJobApplier()
        
        # Run the application
        email_applier.run()
        
    except Exception as e:
        print(f"Failed to start email job applier: {e}")
        logging.error(f"Failed to start: {e}")

if __name__ == "__main__":
    main()
