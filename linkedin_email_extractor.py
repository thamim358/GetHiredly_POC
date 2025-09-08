'''
LinkedIn Job Email Extractor and Auto Sender
Author: Thamim Ansari
LinkedIn: https://www.linkedin.com/in/thamim358/

This script searches for jobs on LinkedIn, extracts emails, and sends applications automatically.
Run this script independently or alongside your             search_url = f"https://www.linkedin.com/jobs/search/?keywords={search_term}&location={self.location}"
            logging.info(f"Searching for: {search_term}")
            
            self.driver.get(search_url)
            buffer(3)ing job applier.

Version: 1.0.0
'''

import os
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
import csv

# Try to import from existing config, fallback to defaults if not available
try:
    from email_config import *
    config_loaded = True
except ImportError:
    config_loaded = False

# Import LinkedIn credentials and helper functions
try:
    from config.secrets import username, password
    linkedin_credentials_available = True
except ImportError:
    linkedin_credentials_available = False
    username = "your_linkedin_email@gmail.com"
    password = "your_linkedin_password"

# Import helper functions for LinkedIn automation
try:
    from modules.helpers import print_lg, buffer
    from modules.clickers_and_finders import text_input_by_ID, try_linkText, try_xp
    linkedin_helpers_available = True
except ImportError:
    linkedin_helpers_available = False
    def print_lg(msg): print(msg)
    def buffer(seconds): time.sleep(seconds)

if not config_loaded:
    try:
        from config.personals import current_city
        from config.search import search_terms as config_search_terms, date_posted as config_date_posted
        SEARCH_LOCATION = current_city
        SEARCH_TERMS = config_search_terms
        DATE_POSTED = config_date_posted
    except ImportError:
        print("Warning: Could not import from config files. Using default values.")
        SEARCH_LOCATION = "India"
        SEARCH_TERMS = ["React Developer", "Frontend Developer", "React.js Developer"]
        DATE_POSTED = "Past 24 hours"
        SENDER_EMAIL = "thamimansari358@gmail.com"
        SENDER_PASSWORD = "fjld gcow xequ fhgp"
        RESUME_FILE = "Thamim_Ansari_Resume.pdf"
        EMAIL_SUBJECT = "Application for React.js Developer / Frontend Developer – 3+ Years Experience"
        EMAIL_BODY = """<html><body><p>Dear Hiring Manager,</p><p>I am interested in the React.js Developer position...</p></body></html>"""
        MAX_JOBS_PER_SEARCH = 25
        DELAY_BETWEEN_EMAILS = 2
        DELAY_BETWEEN_JOBS = 1
        MAX_JOBS_PER_SEARCH = 25
        DELAY_BETWEEN_EMAILS = 2
        DELAY_BETWEEN_JOBS = 1

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
except ImportError:
    print("Error: Selenium is not installed. Please install it using: pip install selenium")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_email_extractor.log'),
        logging.StreamHandler()
    ]
)

class LinkedInEmailExtractor:
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Load job configuration from dashboard if available
        self.load_job_configuration()
        
        # Use configuration from email_config.py or fallback values
        self.SMTP_SERVER = SMTP_SERVER if 'SMTP_SERVER' in globals() else "smtp.gmail.com"
        self.SMTP_PORT = SMTP_PORT if 'SMTP_PORT' in globals() else 587
        self.SENDER_EMAIL = SENDER_EMAIL if 'SENDER_EMAIL' in globals() else "thamimansari358@gmail.com"
        self.SENDER_PASSWORD = SENDER_PASSWORD if 'SENDER_PASSWORD' in globals() else "fjld gcow xequ fhgp"
        
        # Job search configuration
        self.search_terms = SEARCH_TERMS if 'SEARCH_TERMS' in globals() else ["React js Developer", "Frontend Developer"]
        self.location = SEARCH_LOCATION if 'SEARCH_LOCATION' in globals() else "India"
        
        # Email template
        self.SUBJECT = EMAIL_SUBJECT if 'EMAIL_SUBJECT' in globals() else "Application for React.js Developer / Frontend Developer – 3+ Years Experience"
        self.BODY_HTML = EMAIL_BODY if 'EMAIL_BODY' in globals() else """
        <html>
        <body>
            <p>Dear Hiring Manager,</p>
            <p>I am writing to express my interest in the React.js Developer position...</p>
            <p>Best regards,<br>Thamim Ansari</p>
        </body>
        </html>
        """
        
        self.ATTACHMENT_PATH = RESUME_FILE if 'RESUME_FILE' in globals() else "Thamim_Ansari_Resume.pdf"
        self.max_jobs_per_search = MAX_JOBS_PER_SEARCH if 'MAX_JOBS_PER_SEARCH' in globals() else 25
        self.delay_between_emails = DELAY_BETWEEN_EMAILS if 'DELAY_BETWEEN_EMAILS' in globals() else 2
        self.delay_between_jobs = DELAY_BETWEEN_JOBS if 'DELAY_BETWEEN_JOBS' in globals() else 1
        self.date_posted = DATE_POSTED if 'DATE_POSTED' in globals() else "Past 24 hours"
        
        # Statistics
        self.emails_extracted = 0
        self.emails_sent = 0
        self.emails_failed = 0
        self.posts_processed = 0
        
        # Email patterns for extraction
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]
        
        # Store extracted emails to avoid duplicates
        self.extracted_emails: Set[str] = set()
        self.sent_emails: Set[str] = self.load_sent_emails()
        
        # Load job configuration from dashboard (must be called after setting default values)
        self.load_job_configuration()

    def load_job_configuration(self):
        """Load comprehensive job configuration from professional dashboard"""
        try:
            # Check for job configuration from dashboard
            if os.path.exists('temp_job_config.json'):
                with open('temp_job_config.json', 'r') as f:
                    job_config = json.load(f)
                    
                print(f"🎯 Loading job configuration from professional dashboard...")
                print(f"📝 Job Role: {job_config.get('subject', 'Unknown role')}")
                
                # Update instance variables with job-specific configuration
                if 'subject' in job_config:
                    self.SUBJECT = job_config['subject']
                    print(f"✉️ Email Subject: {self.SUBJECT}")
                
                if 'email_body' in job_config:
                    self.BODY_HTML = job_config['email_body']
                    print(f"📄 Email Body: Updated to role-specific template")
                
                if 'search_terms' in job_config:
                    self.search_terms = job_config['search_terms']
                    print(f"🔍 Search Terms: {self.search_terms}")
                
                if 'resume_file' in job_config:
                    # Check for uploaded resume first
                    uploaded_resume = 'uploads/uploaded_resume.pdf'
                    if os.path.exists(uploaded_resume):
                        self.ATTACHMENT_PATH = uploaded_resume
                        print(f"📎 Using uploaded resume: {uploaded_resume}")
                    else:
                        self.ATTACHMENT_PATH = job_config['resume_file']
                        print(f"📎 Resume File: {self.ATTACHMENT_PATH}")
                
                # Load user information for personalization
                if 'user_info' in job_config:
                    user_info = job_config['user_info']
                    self.user_name = user_info.get('name', 'User')
                    self.user_email = user_info.get('email', 'user@example.com')
                    self.user_phone = user_info.get('phone', '')
                    self.user_location = user_info.get('location', 'Location')
                    self.user_website = user_info.get('website', '')
                    print(f"👤 User: {self.user_name} ({self.user_email})")
                    print(f"📍 Location: {self.user_location}")
                
                # Load LinkedIn credentials if available
                try:
                    if os.path.exists('linkedin_credentials.json'):
                        with open('linkedin_credentials.json', 'r') as f:
                            linkedin_creds = json.load(f)
                            self.linkedin_email = linkedin_creds.get('email', '')
                            self.linkedin_password = linkedin_creds.get('password', '')
                            print(f"🔐 LinkedIn credentials loaded for: {self.linkedin_email}")
                except Exception as e:
                    print(f"⚠️ Could not load LinkedIn credentials: {e}")
                
                # Also update global variables for compatibility
                global EMAIL_SUBJECT, EMAIL_BODY, SEARCH_TERMS, RESUME_FILE
                EMAIL_SUBJECT = self.SUBJECT
                EMAIL_BODY = self.BODY_HTML
                SEARCH_TERMS = self.search_terms
                RESUME_FILE = self.ATTACHMENT_PATH
                
                print(f"✅ Professional configuration loaded successfully!")
                
                # Save a copy for reference but don't delete (for debugging)
                with open('last_job_config.json', 'w') as f:
                    json.dump(job_config, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Could not load job configuration: {e}")
            print("📋 Using default configuration...")
            # Initialize user info with defaults
            self.user_name = "User"
            self.user_email = "user@example.com"
            self.user_phone = ""
            self.user_location = "India"
            self.user_website = ""
            self.linkedin_email = username if linkedin_credentials_available else ""
            self.linkedin_password = password if linkedin_credentials_available else ""

    def load_sent_emails(self) -> Set[str]:
        """Load previously sent emails from CSV file"""
        sent_emails = set()
        try:
            if os.path.isfile("sent_emails_log.csv"):
                with open("sent_emails_log.csv", 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        sent_emails.add(row['email'].lower())
        except Exception as e:
            logging.error(f"Error loading sent emails: {e}")
        return sent_emails

    def setup_driver(self):
        """Setup Chrome WebDriver with same options as runAiBot"""
        try:
            # Try different ChromeDriver paths
            chromedriver_paths = [
                "setup/chromedriver/chromedriver.exe",
                "setup\\chromedriver\\chromedriver.exe",
                "chromedriver.exe",
                "./setup/chromedriver/chromedriver.exe"
            ]
            
            service = None
            for path in chromedriver_paths:
                if os.path.exists(path):
                    service = Service(path)
                    print_lg(f"✅ Found ChromeDriver at: {path}")
                    break
            
            if not service:
                # Try using system PATH
                print_lg("⚠️ ChromeDriver not found in local paths, trying system PATH...")
                service = Service()
            
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            
            print_lg("🚀 Starting Chrome WebDriver...")
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 20)
            print_lg("✅ WebDriver setup completed successfully!")
            buffer(1)
            
        except Exception as e:
            logging.error(f"❌ Failed to setup WebDriver: {e}")
            print_lg(f"❌ Failed to setup WebDriver: {e}")
            print_lg("💡 Troubleshooting tips:")
            print_lg("   1. Make sure Chrome browser is installed")
            print_lg("   2. Check if ChromeDriver exists in setup/chromedriver/")
            print_lg("   3. Verify ChromeDriver version matches Chrome version")
            raise e

    def is_logged_in_LN(self) -> bool:
        """Check if user is logged-in in LinkedIn (same as runAiBot)"""
        if self.driver.current_url == "https://www.linkedin.com/feed/": 
            return True
        if linkedin_helpers_available:
            if try_linkText(self.driver, "Sign in"): 
                return False
            if try_xp(self.driver, '//button[@type="submit" and contains(text(), "Sign in")]', click=False):  
                return False
            if try_linkText(self.driver, "Join now"): 
                return False
        print_lg("Didn't find Sign in link, so assuming user is logged in!")
        return True

    def login_to_linkedin(self):
        """Login to LinkedIn using the same method as runAiBot"""
        try:
            print_lg("Attempting to navigate to LinkedIn login page...")
            self.driver.get("https://www.linkedin.com/login")
            
            if not self.is_logged_in_LN():
                print_lg("Not logged in to LinkedIn, attempting login...")
                self.login_LN()
            else:
                print_lg("Already logged in to LinkedIn!")
                
        except Exception as e:
            logging.error(f"Login failed: {e}")
            raise e

    def login_LN(self) -> None:
        """Login function (same as runAiBot)"""
        try:
            self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?")))
            try:
                if linkedin_helpers_available:
                    text_input_by_ID(self.driver, "username", username, 1)
                else:
                    username_field = self.driver.find_element(By.ID, "username")
                    username_field.clear()
                    username_field.send_keys(username)
            except Exception as e:
                print_lg("Couldn't find username field.")
                
            try:
                if linkedin_helpers_available:
                    text_input_by_ID(self.driver, "password", password, 1)
                else:
                    password_field = self.driver.find_element(By.ID, "password")
                    password_field.clear()
                    password_field.send_keys(password)
            except Exception as e:
                print_lg("Couldn't find password field.")
                
            # Find the login submit button and click it
            self.driver.find_element(By.XPATH, '//button[@type="submit" and contains(text(), "Sign in")]').click()
        except Exception as e1:
            try:
                if linkedin_helpers_available:
                    profile_button = self.driver.find_element(By.CLASS_NAME, "profile__details")
                    profile_button.click()
                else:
                    print_lg("Couldn't find saved profile button")
            except Exception as e2:
                print_lg("Couldn't Login!")

        try:
            # Wait until successful redirect, indicating successful login
            self.wait.until(EC.url_to_be("https://www.linkedin.com/feed/"))
            print_lg("Login successful!")
        except Exception as e:
            print_lg("Login might have failed or requires manual intervention!")

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
            # Basic validation and filter out common false positives
            if ('@' in email and '.' in email.split('@')[1] and 
                not any(invalid in email for invalid in ['noreply', 'no-reply', 'donotreply', 'example.com', 'test.com', 'linkedin.com'])):
                cleaned_emails.append(email)
        
        return list(set(cleaned_emails))  # Remove duplicates

    def search_posts(self, search_term: str):
        """Search for posts with given search term and filter by Posts"""
        try:
            # Use LinkedIn search for posts with hiring keyword
            search_url = f"https://www.linkedin.com/search/results/content/?keywords={search_term}%20hiring&origin=SWITCH_SEARCH_VERTICAL"
            logging.info(f"🔍 Searching for posts with: '{search_term}'")
            logging.info(f"🌐 Search URL: {search_url}")
            
            self.driver.get(search_url)
            buffer(3)
            
            # Apply Posts filter
            try:
                # Click on Posts filter button
                posts_filter_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@aria-label, 'Filter by: Posts') and contains(@class, 'search-reusables__filter-pill-button')]")
                ))
                posts_filter_button.click()
                buffer(2)
                logging.info("✅ Applied 'Posts' filter")
                
            except Exception as e:
                logging.warning(f"⚠️ Could not apply Posts filter: {e}")
                # Try alternative method to filter by posts
                try:
                    posts_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Posts')]")
                    posts_button.click()
                    buffer(2)
                    logging.info("Applied 'Posts' filter (alternative method)")
                except:
                    logging.warning("Could not apply Posts filter with alternative method")
            
            # Apply date filter if available
            try:
                # Look for date filter
                date_filter_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Date posted filter')]")
                date_filter_button.click()
                buffer(2)
                
                # Select the configured date option
                date_option_text = getattr(self, 'date_posted', DATE_POSTED)
                logging.info(f"Trying to apply date filter: {date_option_text}")
                
                # Map date options to possible LinkedIn text variations
                date_mappings = {
                    "Past 24 hours": ["Past 24 hours", "24 hours", "Past day"],
                    "Past week": ["Past week", "Week", "7 days"],
                    "Past month": ["Past month", "Month", "30 days"],
                    "Any time": ["Any time", "All time"]
                }
                
                filter_applied = False
                if date_option_text in date_mappings:
                    for option_text in date_mappings[date_option_text]:
                        try:
                            date_option = self.driver.find_element(By.XPATH, f"//label[contains(text(), '{option_text}')]")
                            date_option.click()
                            buffer(1)
                            
                            # Apply filter
                            apply_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Apply')]")
                            apply_button.click()
                            buffer(3)
                            
                            logging.info(f"Applied '{option_text}' date filter")
                            filter_applied = True
                            break
                        except:
                            continue
                
                if not filter_applied:
                    logging.warning(f"Could not find date filter option for: {date_option_text}")
                
            except Exception as e:
                logging.warning(f"Could not apply date filter: {e}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error searching for posts: {e}")
            return False

    def extract_emails_from_posts(self, max_posts: int = 50):
        """Extract emails from LinkedIn posts on current page"""
        try:
            # Scroll to load more posts
            self.scroll_and_load_posts()
            
            # Wait for posts to load
            self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class, 'feed-shared-update-v2') or contains(@class, 'update-components-post')]")
            ))
            
            # Find all posts
            post_elements = self.driver.find_elements(
                By.XPATH, "//div[contains(@class, 'feed-shared-update-v2') or contains(@class, 'update-components-post')]"
            )
            
            logging.info(f"Found {len(post_elements)} posts on this page")
            
            for i, post_element in enumerate(post_elements[:max_posts]):
                try:
                    self.posts_processed += 1
                    logging.info(f"Processing post {self.posts_processed}/{min(max_posts, len(post_elements))}")
                    
                    # Scroll to the post to make it visible
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", post_element)
                    buffer(1)
                    
                    # Extract text from post
                    post_text = ""
                    try:
                        post_text = post_element.text
                    except:
                        pass
                    
                    # Use the comprehensive expand function to reveal full content
                    expanded = self.expand_post_content(post_element)
                    if expanded:
                        # Get expanded text after expansion
                        try:
                            post_text = post_element.text
                            logging.info(f"Successfully expanded post {self.posts_processed} content")
                        except:
                            pass
                    
                    # Extract emails from post text
                    if post_text:
                        post_emails = self.extract_emails_from_text(post_text)
                        if post_emails:
                            logging.info(f"Found emails in post {self.posts_processed}: {post_emails}")
                            self.extracted_emails.update(post_emails)
                            
                            # Send emails immediately
                            for email in post_emails:
                                if email.lower() not in self.sent_emails:
                                    self.send_email(email)
                                    buffer(self.delay_between_emails)  # Configurable delay between emails
                    
                    buffer(self.delay_between_jobs)  # Configurable delay between posts
                    
                except Exception as e:
                    logging.error(f"Error processing post {i+1}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting emails from posts: {e}")
            return False

    def extract_emails_from_posts_continuously(self):
        """Continuously scroll and extract emails from LinkedIn posts"""
        try:
            logging.info("Starting continuous email extraction from posts...")
            processed_post_ids = set()  # Track processed posts to avoid duplicates
            
            # Initial scroll to load posts
            self.scroll_and_load_posts()
            
            consecutive_no_new_posts = 0
            max_consecutive_no_new = 3  # Stop if no new posts found for 3 consecutive attempts
            
            while consecutive_no_new_posts < max_consecutive_no_new:
                # Wait for posts to load
                try:
                    self.wait.until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//div[contains(@class, 'feed-shared-update-v2') or contains(@class, 'update-components-post')]")
                    ))
                except:
                    logging.warning("No posts found, scrolling to load more...")
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    buffer(3)
                    continue
                
                # Find all posts
                post_elements = self.driver.find_elements(
                    By.XPATH, "//div[contains(@class, 'feed-shared-update-v2') or contains(@class, 'update-components-post')]"
                )
                
                logging.info(f"Found {len(post_elements)} posts on current page")
                
                new_posts_found = 0
                
                for i, post_element in enumerate(post_elements):
                    try:
                        # Generate a unique ID for each post to avoid reprocessing
                        post_id = post_element.get_attribute('data-id') or f"post_{i}_{len(post_element.text[:50])}"
                        
                        if post_id in processed_post_ids:
                            continue  # Skip already processed posts
                        
                        processed_post_ids.add(post_id)
                        new_posts_found += 1
                        self.posts_processed += 1
                        
                        logging.info(f"Processing post {self.posts_processed} (ID: {post_id[:20]}...)")
                        
                        # Scroll to the post to make it visible
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post_element)
                        buffer(1)
                        
                        # Extract text from post
                        post_text = ""
                        try:
                            post_text = post_element.text
                        except:
                            pass
                        
                        # Use the comprehensive expand function to reveal full content
                        expanded = self.expand_post_content(post_element)
                        if expanded:
                            # Get expanded text after expansion
                            try:
                                post_text = post_element.text
                                logging.info(f"Successfully expanded post {self.posts_processed} content")
                            except:
                                pass
                        
                        # Extract emails from post text
                        if post_text:
                            post_emails = self.extract_emails_from_text(post_text)
                            if post_emails:
                                logging.info(f"Found emails in post {self.posts_processed}: {post_emails}")
                                self.extracted_emails.update(post_emails)
                                
                                # Send emails immediately
                                for email in post_emails:
                                    if email.lower() not in self.sent_emails:
                                        self.send_email(email)
                                        buffer(self.delay_between_emails)  # Configurable delay between emails
                        
                        buffer(self.delay_between_jobs)  # Configurable delay between posts
                        
                    except Exception as e:
                        logging.error(f"Error processing post {i+1}: {e}")
                        continue
                
                if new_posts_found == 0:
                    consecutive_no_new_posts += 1
                    logging.info(f"No new posts found. Attempt {consecutive_no_new_posts}/{max_consecutive_no_new}")
                else:
                    consecutive_no_new_posts = 0  # Reset counter when new posts are found
                    logging.info(f"Processed {new_posts_found} new posts")
                    
                    # Update runtime stats for dashboard
                    self._update_runtime_stats()
                
                # Scroll down to load more posts
                logging.info("Scrolling to load more posts...")
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                buffer(3)  # Wait for posts to load
                
                # Check if new content was loaded
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    consecutive_no_new_posts += 1
                    logging.info("No new content loaded after scrolling")
                else:
                    logging.info("New content loaded, continuing...")
            
            logging.info("Finished continuous email extraction")
            
        except Exception as e:
            logging.error(f"Error in continuous email extraction: {e}")
            return False
                    
    def expand_post_content(self, post_element):
        """Try multiple methods to expand post content and reveal hidden emails"""
        expanded = False
        
        # Method 1: Look for the specific "see more" button with exact classes
        try:
            see_more_buttons = post_element.find_elements(By.XPATH, 
                ".//button[contains(@class, 'feed-shared-inline-show-more-text__see-more-less-toggle')]"
            )
            for button in see_more_buttons:
                if button.is_displayed() and button.is_enabled():
                    # Scroll to button and ensure it's visible
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                    buffer(1)
                    # Try clicking with JavaScript if regular click fails
                    try:
                        button.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", button)
                    buffer(2)
                    expanded = True
                    logging.info("Expanded content using specific see-more button")
                    break
        except Exception as e:
            logging.debug(f"Method 1 failed: {e}")
        
        # Method 2: Look for any "...more" or "see more" text/button
        if not expanded:
            try:
                more_selectors = [
                    ".//button[contains(text(), '…more')]",
                    ".//button[contains(text(), 'see more')]", 
                    ".//button[contains(text(), 'See more')]",
                    ".//span[contains(text(), '…more')]",
                    ".//span[contains(text(), 'see more')]"
                ]
                
                for selector in more_selectors:
                    buttons = post_element.find_elements(By.XPATH, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            try:
                                # Try to click the button or its parent if it's a span
                                if button.tag_name == 'span':
                                    # If it's a span, try to find clickable parent
                                    clickable_parent = button.find_element(By.XPATH, "./ancestor::button[1]")
                                    clickable_parent.click()
                                else:
                                    button.click()
                                buffer(2)
                                expanded = True
                                logging.info(f"Expanded content using selector: {selector}")
                                break
                            except:
                                continue
                    if expanded:
                        break
            except Exception as e:
                logging.debug(f"Method 2 failed: {e}")
        
        # Method 3: Look for truncated text and try to expand
        if not expanded:
            try:
                # Look for elements that might contain truncated text
                text_elements = post_element.find_elements(By.XPATH, 
                    ".//div[contains(@class, 'feed-shared-text') or contains(@class, 'update-components-text')]"
                )
                for text_elem in text_elements:
                    if '…' in text_elem.text or text_elem.text.endswith('...'):
                        # Try clicking on the text element itself
                        try:
                            text_elem.click()
                            buffer(2)
                            expanded = True
                            logging.info("Expanded content by clicking on truncated text")
                            break
                        except:
                            continue
            except Exception as e:
                logging.debug(f"Method 3 failed: {e}")
        
        # Method 4: Look for show more toggle buttons
        if not expanded:
            try:
                toggle_buttons = post_element.find_elements(By.XPATH, 
                    ".//button[contains(@class, 'show-more') or contains(@aria-label, 'see more')]"
                )
                for button in toggle_buttons:
                    if button.is_displayed():
                        button.click()
                        buffer(2)
                        expanded = True
                        logging.info("Expanded content using toggle button")
                        break
            except Exception as e:
                logging.debug(f"Method 4 failed: {e}")
        
        return expanded

    def scroll_and_load_posts(self):
        """Scroll down to load more posts"""
        try:
            logging.info("Scrolling to load more posts...")
            
            # Get initial height
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            for scroll_attempt in range(3):  # Scroll 3 times to load more posts
                # Scroll down to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                buffer(3)  # Wait for new posts to load
                
                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    logging.info("No more posts to load")
                    break
                    
                last_height = new_height
                logging.info(f"Scrolled {scroll_attempt + 1}/3 times, loaded more posts")
            
            # Scroll back to top to start processing
            self.driver.execute_script("window.scrollTo(0, 0);")
            buffer(2)
            
        except Exception as e:
            logging.error(f"Error scrolling to load posts: {e}")

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
            logging.warning(f"Resume file {self.ATTACHMENT_PATH} not found!")
        
        return msg

    def send_email(self, to_email: str) -> bool:
        """Send email to a specific address"""
        try:
            if to_email.lower() in self.sent_emails:
                logging.info(f"Email already sent to {to_email}, skipping...")
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
            self.sent_emails.add(to_email.lower())
            logging.info(f"✓ Email sent successfully to {to_email}")
            
            # Save sent email to file
            self.save_sent_email(to_email)
            
            return True
            
        except Exception as e:
            self.emails_failed += 1
            logging.error(f"✗ Failed to send email to {to_email}: {str(e)}")
            return False

    def save_sent_email(self, email: str):
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
            logging.error(f"Failed to save sent email log: {e}")

    def save_extracted_emails(self):
        """Save all extracted emails to JSON file with detailed stats for dashboard"""
        try:
            stats_data = {
                'emails': list(self.extracted_emails),
                'total_count': len(self.extracted_emails),
                'emails_sent': self.emails_sent,
                'emails_failed': self.emails_failed,
                'posts_processed': self.posts_processed,
                'success_rate': (self.emails_sent / len(self.extracted_emails) * 100) if len(self.extracted_emails) > 0 else 0,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'timestamp': datetime.now().isoformat()
            }
            
            with open('extracted_emails.json', 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2)
                
            # Also update stats during runtime for real-time dashboard updates
            self._update_runtime_stats()
            
        except Exception as e:
            logging.error(f"Failed to save extracted emails: {e}")

    def _update_runtime_stats(self):
        """Update runtime statistics file for dashboard"""
        try:
            runtime_stats = {
                'email_extractor': {
                    'emails_extracted': len(self.extracted_emails),
                    'emails_sent': self.emails_sent,
                    'emails_failed': self.emails_failed,
                    'posts_processed': self.posts_processed,
                    'status': 'running',
                    'last_updated': datetime.now().isoformat()
                }
            }
            
            with open('dashboard_stats.json', 'w', encoding='utf-8') as f:
                json.dump(runtime_stats, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to update runtime stats: {e}")

    def run(self):
        """Main execution function"""
        try:
            logging.info("Starting LinkedIn Email Extractor...")
            
            # Setup WebDriver
            self.setup_driver()
            
            # Login to LinkedIn
            self.login_to_linkedin()
            
            # Display current configuration
            logging.info(f"\n{'='*60}")
            logging.info("CURRENT CONFIGURATION")
            logging.info(f"{'='*60}")
            logging.info(f"📧 Email Subject: {self.SUBJECT}")
            logging.info(f"🔍 Search Terms: {self.search_terms}")
            logging.info(f"📎 Resume File: {self.ATTACHMENT_PATH}")
            logging.info(f"📍 Location: {self.location}")
            logging.info(f"{'='*60}")
            
            # Use the first search term for initial search
            search_term = self.search_terms[0] if self.search_terms else "React Developer"
            logging.info(f"\n{'='*60}")
            logging.info(f"🎯 Processing search term: {search_term}")
            logging.info(f"📋 Available terms: {', '.join(self.search_terms)}")
            logging.info(f"{'='*60}")
            
            if self.search_posts(search_term):
                # Continuously extract emails from posts without limit
                self.extract_emails_from_posts_continuously()
            
            # Save extracted emails
            self.save_extracted_emails()
            
            # Print statistics
            logging.info(f"\n{'='*60}")
            logging.info("FINAL STATISTICS")
            logging.info(f"{'='*60}")
            logging.info(f"Posts processed: {self.posts_processed}")
            logging.info(f"Unique emails extracted: {len(self.extracted_emails)}")
            logging.info(f"Emails sent successfully: {self.emails_sent}")
            logging.info(f"Emails failed: {self.emails_failed}")
            if len(self.extracted_emails) > 0:
                success_rate = (self.emails_sent / len(self.extracted_emails)) * 100
                logging.info(f"Success rate: {success_rate:.1f}%")
            logging.info(f"{'='*60}")
            
        except Exception as e:
            logging.error(f"Critical error: {e}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    logging.info("Browser closed successfully")
                except:
                    pass

def main():
    """Main function"""
    print("LinkedIn Posts Email Extractor and Auto Sender")
    print("=" * 50)
    print("This tool will:")
    print("1. Search for React/Frontend developer posts on LinkedIn")
    print("2. Filter by Posts and scroll through them")
    print("3. Extract email addresses from hiring posts")
    print("4. Send personalized job applications via email")
    print("5. Track sent emails to avoid duplicates")
    print("\nMake sure you have:")
    print("- Chrome browser installed")
    print("- Your resume file 'Thamim_Ansari_Resume.pdf' in the current directory")
    print("- Valid LinkedIn credentials")
    print("\nStarting in 5 seconds...")
    
    time.sleep(5)
    
    try:
        extractor = LinkedInEmailExtractor()
        extractor.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
