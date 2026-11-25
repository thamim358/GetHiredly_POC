'''
LinkedIn Job Email Extractor and Auto Sender
Author: Thamim Ansari
LinkedIn: https://www.linkedin.com/in/thamim358/

This script searches for LinkedIn posts, extracts emails from hiring posts,
and sends personalized job applications via email automatically.
Run this script independently or through the dashboard.

Version: 1.0.0
'''

# Set console encoding to UTF-8 to handle Unicode characters properly
import os
import sys
if os.name == 'nt':  # Windows
    os.system('chcp 65001 > nul')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import re
import time
import json
import smtplib
import logging
import urllib.parse
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Set
import csv
import hashlib
from email_formatting import render_email_html, plain_text_from_html

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

def buffer(seconds):
    time.sleep(seconds)

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
        SENDER_EMAIL = "your.email@gmail.com"
        SENDER_PASSWORD = "your-16-character-app-password"
        RESUME_FILE = "uploads/uploaded_resume.pdf"
        EMAIL_SUBJECT = "Application for React.js Developer / Frontend Developer – 3+ Years Experience"
        EMAIL_BODY = "Dear Hiring Manager,\n\nI am interested in the React.js Developer position.\n\nBest regards,\n[FULL_NAME]"
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
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
except ImportError:
    print("Error: Selenium is not installed. Please install it using: pip install selenium")
    exit(1)

# Configure logging with UTF-8 encoding to handle Unicode characters
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_email_extractor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)


def print_lg(*messages):
    """Log extractor messages without the main bot's GUI log-file prompt."""
    logging.info(" ".join(str(message) for message in messages))


LOGIN_EMAIL_SELECTOR = "input#username, input[name='session_key'], input[type='email'][autocomplete^='username']"
LOGIN_PASSWORD_SELECTOR = "input#password, input[name='session_password'], input[type='password'][autocomplete='current-password']"
POST_XPATH = ("//div[contains(@class, 'feed-shared-update-v2') or contains(@class, 'update-components-post')]"
              " | //div[@role='listitem'][.//h2[contains(normalize-space(.), 'Feed post')]]")

class LinkedInEmailExtractor:
    def __init__(self):
        self.driver = None
        self.wait = None

        # Use configuration from email_config.py or fallback values
        self.SMTP_SERVER = SMTP_SERVER if 'SMTP_SERVER' in globals() else "smtp.gmail.com"
        self.SMTP_PORT = SMTP_PORT if 'SMTP_PORT' in globals() else 587
        self.SENDER_EMAIL = SENDER_EMAIL if 'SENDER_EMAIL' in globals() else "your.email@gmail.com"
        self.SENDER_PASSWORD = SENDER_PASSWORD if 'SENDER_PASSWORD' in globals() else "your-16-character-app-password"

        # Job search configuration
        self.search_terms = SEARCH_TERMS if 'SEARCH_TERMS' in globals() else ["React js Developer", "Frontend Developer"]
        self.location = SEARCH_LOCATION if 'SEARCH_LOCATION' in globals() else "India"

        # Target companies and countries configuration
        self.target_companies = []  # List of target companies like ["Google", "Microsoft", "Amazon"]
        self.target_countries = []  # List of target countries/locations like ["UAE", "USA", "Canada"]

        # Email preferences - unlimited sending enabled
        self.emails_sent_today = 0
        self.last_email_time = None
        self.current_date = date.today()  # Track current date for daily reset
        self.allow_fresh_campaign = True  # Allow option to start fresh campaigns

        # Sending limits (overridden by dashboard job configuration when available)
        self.emails_per_hour = 0
        self.daily_limit = 0
        self.skip_weekends = False
        self.daily_limit_reached = False
        self.sent_times = []  # Timestamps of emails sent, for hourly limit tracking

        # Email template
        self.SUBJECT = EMAIL_SUBJECT if 'EMAIL_SUBJECT' in globals() else "Application for React.js Developer / Frontend Developer – 3+ Years Experience"
        self.BODY_HTML = EMAIL_BODY if 'EMAIL_BODY' in globals() else (
            "Dear Hiring Manager,\n\nI am interested in the React.js Developer position.\n\n"
            "Best regards,\n[FULL_NAME]"
        )

        self.ATTACHMENT_PATH = RESUME_FILE if 'RESUME_FILE' in globals() else "uploads/uploaded_resume.pdf"
        self.campaign_roles = []
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
                    print(f"[EMAIL] Email Subject: {self.SUBJECT}")

                if 'email_body' in job_config:
                    self.BODY_HTML = job_config['email_body']
                    print(f"📄 Email Body: Updated to role-specific template with proper formatting")

                if 'search_terms' in job_config:
                    self.search_terms = job_config['search_terms']
                    print(f"[SEARCH] Search Terms: {self.search_terms}")

                # Load target companies configuration
                if 'target_companies' in job_config:
                    self.target_companies = job_config['target_companies']
                    print(f"[COMPANIES] Target Companies: {self.target_companies}")
                elif 'companyFilter' in job_config and job_config['companyFilter'].get('enabled', False):
                    # Extract company names from the new structure
                    self.target_companies = [company.get('name', company) if isinstance(company, dict) else company
                                           for company in job_config['companyFilter'].get('companies', [])]
                    print(f"[COMPANIES] Target Companies (from filter): {self.target_companies}")

                # Load target countries/locations configuration
                if 'target_countries' in job_config:
                    self.target_countries = job_config['target_countries']
                    print(f"[COUNTRIES] Target Countries/Locations: {self.target_countries}")
                elif 'countryFilter' in job_config and job_config['countryFilter'].get('enabled', False):
                    # Extract country search terms from the new structure
                    self.target_countries = [country.get('searchTerms', country.get('name', country)) if isinstance(country, dict) else country
                                           for country in job_config['countryFilter'].get('countries', [])]
                    print(f"[COUNTRIES] Target Countries/Locations (from filter): {self.target_countries}")

                # Check if user wants to start a fresh campaign (clear sent emails) - removed other email limits
                if 'freshCampaign' in job_config and job_config['freshCampaign']:
                    self.clear_sent_emails_log()
                    print(f"🔄 Fresh campaign mode: Cleared sent emails log")

                # Load date filter preference from dashboard
                if 'date_filter' in job_config:
                    # Map dashboard values to LinkedIn filter text
                    date_filter_mapping = {
                        'past-24h': 'Past 24 hours',
                        'past-week': 'Past week',
                        'past-month': 'Past month'
                    }
                    dashboard_filter = job_config['date_filter']
                    self.date_posted = date_filter_mapping.get(dashboard_filter, 'Past week')
                    print(f"[DATE] Date Filter: {self.date_posted} (from: {dashboard_filter})")
                else:
                    self.date_posted = "Past week"  # Default
                    print(f"[DATE] Date Filter: {self.date_posted} (default)")

                # Load email sending limits from dashboard configuration
                try:
                    self.emails_per_hour = max(int(job_config.get('emails_per_hour', 0) or 0), 0)
                except (TypeError, ValueError):
                    self.emails_per_hour = 0
                try:
                    self.daily_limit = max(int(job_config.get('daily_limit', 0) or 0), 0)
                except (TypeError, ValueError):
                    self.daily_limit = 0
                self.skip_weekends = bool(job_config.get('skip_weekends', False))
                self.daily_limit_reached = False
                self.sent_times = []
                if self.daily_limit or self.emails_per_hour or self.skip_weekends:
                    print(f"[LIMITS] Emails/hour: {self.emails_per_hour}, Daily limit: {self.daily_limit}, Skip weekends: {self.skip_weekends}")

                if 'resume_file' in job_config:
                    self.ATTACHMENT_PATH = job_config['resume_file']
                    if not os.path.isfile(self.ATTACHMENT_PATH):
                        raise FileNotFoundError(f"Configured resume is missing: {self.ATTACHMENT_PATH}")
                self.campaign_roles = job_config.get('roles') or [{
                    'role': job_config.get('job_role', 'custom'),
                    'subject': self.SUBJECT,
                    'email_body': self.BODY_HTML,
                    'search_terms': self.search_terms,
                    'resume_file': self.ATTACHMENT_PATH,
                }]
                for role in self.campaign_roles:
                    if not os.path.isfile(role['resume_file']):
                        raise FileNotFoundError(f"Configured resume is missing: {role['resume_file']}")

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
                            print(f"[AUTH] LinkedIn credentials loaded for: {self.linkedin_email}")

                            # Load Gmail sender credentials (used for SMTP) from dashboard config
                            gmail_creds = linkedin_creds.get('gmail', {})
                            if gmail_creds.get('senderEmail') and gmail_creds.get('senderPassword'):
                                self.SENDER_EMAIL = gmail_creds['senderEmail'].strip()
                                self.SENDER_PASSWORD = gmail_creds['senderPassword'].strip()
                                print(f"[AUTH] Gmail sender configured for: {self.SENDER_EMAIL}")
                            elif not gmail_creds.get('senderEmail'):
                                print(f"[WARNING] No Gmail sender configured - SMTP will use defaults from email_config.py")
                except Exception as e:
                    print(f"[WARNING] Could not load LinkedIn credentials: {e}")

                # Also update global variables for compatibility
                global EMAIL_SUBJECT, EMAIL_BODY, SEARCH_TERMS, RESUME_FILE
                EMAIL_SUBJECT = self.SUBJECT
                EMAIL_BODY = self.BODY_HTML
                SEARCH_TERMS = self.search_terms
                RESUME_FILE = self.ATTACHMENT_PATH

                print(f"[SUCCESS] Professional configuration loaded successfully!")

                # Save a copy for reference but don't delete (for debugging)
                with open('last_job_config.json', 'w') as f:
                    json.dump(job_config, f, indent=2)

        except (FileNotFoundError, KeyError, ValueError):
            raise
        except Exception as e:
            print(f"[WARNING] Could not load job configuration: {e}")
            print("[INFO] Using default configuration...")
            # Initialize user info with defaults
            self.user_name = "User"
            self.user_email = "user@example.com"
            self.user_phone = ""
            self.user_location = "India"
            self.user_website = ""
            self.linkedin_email = username if linkedin_credentials_available else ""
            self.linkedin_password = password if linkedin_credentials_available else ""

            # Initialize target companies and countries with defaults
            self.target_companies = []
            self.target_countries = []

            # Initialize sending limits with defaults
            self.emails_per_hour = 0
            self.daily_limit = 0
            self.skip_weekends = False
            self.daily_limit_reached = False
            self.sent_times = []

    def load_sent_emails(self) -> Set[str]:
        """Load previously sent emails from CSV file"""
        sent_emails = set()
        try:
            if os.path.isfile("sent_emails_log.csv"):
                with open("sent_emails_log.csv", 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        sent_emails.add(row['email'].lower())
                logging.info(f"[EMAIL] Loaded {len(sent_emails)} previously sent emails")
            else:
                logging.info("[EMAIL] No previous sent emails log found")
        except Exception as e:
            logging.error(f"Error loading sent emails: {e}")
        return sent_emails

    def clear_sent_emails_log(self):
        """Clear the sent emails log to start fresh campaign"""
        try:
            if os.path.exists('sent_emails_log.csv'):
                # Backup existing log before clearing
                backup_name = f"sent_emails_log_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                os.rename('sent_emails_log.csv', backup_name)
                logging.info(f"[EMAIL] Backed up existing log to {backup_name}")

            # Clear in-memory set
            self.sent_emails.clear()
            logging.info(f"[RESET] Cleared sent emails log for fresh campaign")
        except Exception as e:
            logging.error(f"Failed to clear sent emails log: {e}")

    def setup_driver(self):
        """Start Chrome with a driver matching the installed browser."""
        try:
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
            # Selenium Manager chooses the driver for the installed Chrome.
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 20)
            print_lg("✅ WebDriver setup completed successfully!")
            buffer(1)

        except Exception as e:
            logging.error(f"❌ Failed to setup WebDriver: {e}")
            print_lg(f"❌ Failed to setup WebDriver: {e}")
            print_lg("💡 Troubleshooting tips:")
            print_lg("   1. Make sure Chrome browser is installed")
            print_lg("   2. Check that Selenium Manager can download a matching ChromeDriver")
            print_lg("   3. Check that Chrome can start in this Windows session")
            raise e

    def is_logged_in_LN(self) -> bool:
        """Confirm an authenticated LinkedIn page, not just a missing label."""
        path = urllib.parse.urlparse(self.driver.current_url).path.lower()
        authenticated_page = path.startswith(("/feed", "/jobs", "/mynetwork", "/in/"))
        visible_login_fields = any(
            field.is_displayed()
            for field in self.driver.find_elements(By.CSS_SELECTOR, LOGIN_EMAIL_SELECTOR)
        )
        return authenticated_page and not visible_login_fields

    def _visible_login_element(self, selector: str):
        """Find a visible login control when LinkedIn renders hidden duplicates."""
        return WebDriverWait(self.driver, 20).until(
            lambda driver: next(
                (element for element in driver.find_elements(By.CSS_SELECTOR, selector)
                 if element.is_displayed() and element.is_enabled()),
                False,
            )
        )

    def login_to_linkedin(self):
        """Open LinkedIn and submit credentials when the login form is present."""
        try:
            self.update_status("Navigating to LinkedIn login...", 35)
            self.driver.get("https://www.linkedin.com/login")
            WebDriverWait(self.driver, 20).until(
                lambda driver: self.is_logged_in_LN()
                or any(field.is_displayed() for field in driver.find_elements(By.CSS_SELECTOR, LOGIN_EMAIL_SELECTOR))
            )
            if self.is_logged_in_LN():
                logging.info("LinkedIn session is already authenticated")
                self.update_status("Already logged in to LinkedIn", 50)
                return

            self.update_status("Entering credentials...", 40)
            self.login_LN()
            self.update_status("Successfully connected to LinkedIn", 50)
        except Exception as error:
            logging.error("LinkedIn login failed: %s", error)
            self.update_status(f"Login failed: {str(error).splitlines()[0]}", 0)
            raise

    def login_LN(self) -> None:
        """Fill the LinkedIn login form and verify the resulting session."""
        linkedin_user = (getattr(self, "linkedin_email", "") or username).strip()
        linkedin_pass = getattr(self, "linkedin_password", "") or password
        if not linkedin_user or not linkedin_pass:
            raise ValueError("LinkedIn email and password are required")

        email_field = self._visible_login_element(LOGIN_EMAIL_SELECTOR)
        password_field = self._visible_login_element(LOGIN_PASSWORD_SELECTOR)
        email_field.clear()
        email_field.send_keys(linkedin_user)
        password_field.clear()
        password_field.send_keys(linkedin_pass)
        if email_field.get_attribute("value") != linkedin_user or not password_field.get_attribute("value"):
            raise RuntimeError("LinkedIn login fields were not filled")
        logging.info("LinkedIn login fields filled")

        sign_in_button = WebDriverWait(self.driver, 20).until(
            lambda driver: next(
                (button for button in driver.find_elements(
                    By.XPATH, "//button[normalize-space(.)='Sign in']"
                ) if button.is_displayed() and button.is_enabled()),
                False,
            )
        )
        sign_in_button.click()
        self.update_status("Verifying LinkedIn sign-in...", 45)

        try:
            WebDriverWait(self.driver, 25).until(
                lambda driver: self.is_logged_in_LN()
                or "/checkpoint" in driver.current_url
                or "/challenge" in driver.current_url
            )
        except TimeoutException as error:
            raise RuntimeError(
                "LinkedIn sign-in was not confirmed. Check the credentials or any message in the browser."
            ) from error

        if not self.is_logged_in_LN():
            self.update_status("Complete LinkedIn verification in the browser", 45)
            logging.warning("LinkedIn requires a verification step in the browser")
            try:
                WebDriverWait(self.driver, 120).until(lambda driver: self.is_logged_in_LN())
            except TimeoutException as error:
                raise RuntimeError("LinkedIn verification was not completed") from error

        logging.info("LinkedIn sign-in confirmed")

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
            # Map our date options to LinkedIn's URL parameter values
            date_filter_mapping = {
                "Past 24 hours": "past-24h",
                "Past week": "past-week",
                "Past month": "past-month"
            }

            # Get the configured date option and map it to URL parameter
            date_option_text = getattr(self, 'date_posted', 'Past week')
            date_param = date_filter_mapping.get(date_option_text, 'past-week')

            # Build comprehensive search query with + symbols (LinkedIn-friendly)
            search_keywords = [search_term, "hiring"]

            # Add target companies to search if specified
            if hasattr(self, 'target_companies') and self.target_companies:
                # Add companies with + logic - any of these companies
                for company in self.target_companies:
                    search_keywords.append(company)
                logging.info(f"🏢 Including target companies in search: {self.target_companies}")

            # Add target countries/locations to search if specified
            if hasattr(self, 'target_countries') and self.target_countries:
                # Add countries with + logic - any of these locations
                for country in self.target_countries:
                    search_keywords.append(country)
                logging.info(f"🌍 Including target countries/locations in search: {self.target_countries}")

            # Combine all search keywords with + symbols (LinkedIn-friendly format)
            full_search_query = " + ".join(search_keywords)

            # URL encode the search query
            encoded_query = urllib.parse.quote_plus(full_search_query)

            # Build search URL with date filter included
            search_url = f"https://www.linkedin.com/search/results/content/?datePosted=%22{date_param}%22&keywords={encoded_query}&origin=FACETED_SEARCH"

            logging.info(f"🔍 Searching for posts with: '{full_search_query}'")
            logging.info(f"📅 Date filter: {date_option_text} (URL param: {date_param})")
            logging.info(f"🌐 Search URL: {search_url}")

            self.driver.get(search_url)
            buffer(3)

            # The content-results URL already displays posts in LinkedIn's current UI.
            logging.info("Content search results loaded")

            # Note: Date filter is now applied via URL parameter, so we don't need the manual filter click
            logging.info(f"✅ Date filter '{date_option_text}' applied via URL parameter")

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
                (By.XPATH, POST_XPATH)
            ))

            # Find all posts
            post_elements = self.driver.find_elements(
                By.XPATH, POST_XPATH
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
            posts_this_search = 0

            while consecutive_no_new_posts < max_consecutive_no_new and posts_this_search < self.max_jobs_per_search:
                # Stop early when the configured daily email limit is reached
                if getattr(self, 'daily_limit_reached', False):
                    logging.info("[LIMIT] Daily email limit reached - stopping extraction")
                    break
                # Wait for posts to load
                try:
                    self.wait.until(EC.presence_of_all_elements_located(
                        (By.XPATH, POST_XPATH)
                    ))
                except:
                    logging.warning("No posts found, scrolling to load more...")
                    consecutive_no_new_posts += 1
                    self._scroll_results()
                    buffer(3)
                    continue

                # Find all posts
                post_elements = self.driver.find_elements(
                    By.XPATH, POST_XPATH
                )

                logging.info(f"Found {len(post_elements)} posts on current page")

                new_posts_found = 0

                for i, post_element in enumerate(post_elements):
                    try:
                        # Generate a unique ID for each post to avoid reprocessing
                        post_id = post_element.get_attribute('data-id') or hashlib.sha256(post_element.text.encode('utf-8')).hexdigest()

                        if post_id in processed_post_ids:
                            continue  # Skip already processed posts

                        processed_post_ids.add(post_id)
                        new_posts_found += 1
                        posts_this_search += 1
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
                        if posts_this_search >= self.max_jobs_per_search:
                            break

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
                last_height = self._results_scroll_height()
                self._scroll_results()
                buffer(3)  # Wait for posts to load

                # Check if new content was loaded
                new_height = self._results_scroll_height()
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
                    ".//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'more')]"
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

    def _results_scroll_height(self) -> int:
        """Return the height of LinkedIn's scrollable results area."""
        return self.driver.execute_script(
            "const main = document.querySelector('main');"
            "const area = main && main.scrollHeight > main.clientHeight "
            "? main : document.scrollingElement;"
            "return area.scrollHeight;"
        )

    def _scroll_results(self, top: bool = False) -> None:
        """Scroll the results panel, falling back to the document."""
        self.driver.execute_script(
            "const main = document.querySelector('main');"
            "const area = main && main.scrollHeight > main.clientHeight "
            "? main : document.scrollingElement;"
            "area.scrollTop = arguments[0] ? 0 : area.scrollHeight;",
            top,
        )

    def scroll_and_load_posts(self):
        """Position at the first result before processing posts in order."""
        self._scroll_results(top=True)
        buffer(1)

    def create_email_message(self, to_email: str) -> MIMEMultipart:
        """Create email message with attachment and proper HTML formatting"""
        msg = MIMEMultipart('mixed')
        msg['From'] = self.SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = self.SUBJECT

        email_body = render_email_html(self.BODY_HTML)
        alternatives = MIMEMultipart('alternative')
        alternatives.attach(MIMEText(plain_text_from_html(email_body), 'plain', 'utf-8'))
        alternatives.attach(MIMEText(email_body, 'html', 'utf-8'))
        msg.attach(alternatives)

        # Add attachment if exists
        if os.path.isfile(self.ATTACHMENT_PATH):
            try:
                with open(self.ATTACHMENT_PATH, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())

                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(self.ATTACHMENT_PATH)}'
                )
                msg.attach(part)
                logging.info(f"[ATTACH] Resume attached: {self.ATTACHMENT_PATH}")
            except Exception as e:
                logging.error(f"[ERROR] Failed to attach resume {self.ATTACHMENT_PATH}: {e}")
                raise
        else:
            raise FileNotFoundError(f"Configured resume is missing: {self.ATTACHMENT_PATH}")

        return msg

    def send_email(self, to_email: str) -> bool:
        """Send email to a specific address with preference controls"""
        try:
            # Check if we need to reset daily counter (new day)
            today = date.today()
            if today != self.current_date:
                self.emails_sent_today = 0
                self.current_date = today
                logging.info(f"[DATE] New day detected - daily email counter reset")

            # Check if email already sent
            if to_email.lower() in self.sent_emails:
                logging.info(f"[EMAIL] Email already sent to {to_email}, skipping...")
                return False

            # Respect configured sending limits (hourly rate, daily cap, weekends)
            if not self._can_send_email():
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

            # Update tracking
            self.emails_sent += 1
            self.emails_sent_today += 1
            self.sent_emails.add(to_email.lower())
            self.last_email_time = datetime.now()
            self.sent_times.append(time.time())

            logging.info(f"[SUCCESS] Email sent successfully to {to_email} ({self.emails_sent_today} sent today)")

            # Save sent email to file
            self.save_sent_email(to_email)

            return True

        except Exception as e:
            self.emails_failed += 1
            logging.error(f"[ERROR] Failed to send email to {to_email}: {str(e)}")
            return False

    def _can_send_email(self) -> bool:
        """
        Respect configured sending limits.
        Returns True if an email may be sent now, False otherwise.
        - Skip weekends if enabled
        - Enforce daily cap
        - Enforce hourly rate (waits briefly when the hourly window is full)
        """
        # Skip weekends if configured
        if self.skip_weekends and date.today().weekday() >= 5:
            logging.warning("[LIMIT] Skipping email - weekends are disabled by configuration")
            return False

        # Enforce daily limit
        if self.daily_limit and self.emails_sent_today >= self.daily_limit:
            logging.warning(f"[LIMIT] Daily limit reached ({self.daily_limit}) - stopping email sending")
            self.daily_limit_reached = True
            return False

        # Enforce hourly limit
        if self.emails_per_hour:
            cutoff = time.time() - 3600
            self.sent_times = [t for t in self.sent_times if t > cutoff]
            if len(self.sent_times) >= self.emails_per_hour:
                wait_seconds = int(3600 - (time.time() - self.sent_times[0]))
                if wait_seconds > 0:
                    logging.info(f"[LIMIT] Hourly limit reached ({self.emails_per_hour}/hour) - waiting {min(wait_seconds, 300)}s")
                    time.sleep(min(wait_seconds, 300))
                    # Re-check after waiting
                    self.sent_times = [t for t in self.sent_times if t > time.time() - 3600]
                    if len(self.sent_times) >= self.emails_per_hour:
                        logging.warning("[LIMIT] Still over hourly limit - skipping this email")
                        return False

        return True

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

    def update_status(self, status_message, progress=None):
        """Update status file for dashboard monitoring"""
        try:
            status_data = {
                'status': status_message,
                'timestamp': datetime.now().isoformat(),
                'progress': progress
            }
            with open('extractor_status.json', 'w') as f:
                json.dump(status_data, f)
        except Exception as e:
            logging.error(f"Failed to update status: {e}")

    def run(self):
        """Main execution function"""
        try:
            logging.info("Starting LinkedIn Email Extractor...")
            self.update_status("Initializing...", 10)

            # Setup WebDriver
            self.update_status("Setting up browser...", 20)
            self.setup_driver()

            # Login to LinkedIn
            self.update_status("Connecting to LinkedIn...", 30)
            self.login_to_linkedin()
            self.update_status("Successfully connected to LinkedIn", 50)

            # Display current configuration
            logging.info(f"\n{'='*60}")
            logging.info("CURRENT CONFIGURATION")
            logging.info(f"{'='*60}")
            logging.info(f"📧 Email Subject: {self.SUBJECT}")
            logging.info(f"🔍 Search Terms: {self.search_terms}")
            logging.info(f"📎 Resume File: {self.ATTACHMENT_PATH}")
            logging.info(f"📍 Location: {self.location}")

            # Display target companies if configured
            if hasattr(self, 'target_companies') and self.target_companies:
                logging.info(f"🏢 Target Companies: {self.target_companies}")

            # Display target countries if configured
            if hasattr(self, 'target_countries') and self.target_countries:
                logging.info(f"🌍 Target Countries/Locations: {self.target_countries}")

            logging.info(f"{'='*60}")

            # Keep the email template and attachment paired with each role.
            roles = self.campaign_roles or [{
                'role': 'default', 'subject': self.SUBJECT,
                'email_body': self.BODY_HTML, 'search_terms': self.search_terms,
                'resume_file': self.ATTACHMENT_PATH,
            }]
            for role in roles:
                self.SUBJECT = role['subject']
                self.BODY_HTML = role['email_body']
                self.ATTACHMENT_PATH = role['resume_file']
                if not os.path.isfile(self.ATTACHMENT_PATH):
                    raise FileNotFoundError(f"Configured resume is missing: {self.ATTACHMENT_PATH}")
                logging.info("Processing role %s with resume %s", role.get('title', role.get('role')), os.path.basename(self.ATTACHMENT_PATH))
                for search_term in role['search_terms']:
                    if getattr(self, 'daily_limit_reached', False):
                        break
                    self.update_status(f"Searching for {search_term} posts...", 60)
                    if self.search_posts(search_term):
                        self.update_status("Extracting emails from posts...", 70)
                        self.extract_emails_from_posts_continuously()
                    self.save_extracted_emails()
                if getattr(self, 'daily_limit_reached', False):
                    break

            self.update_status("Email extraction completed", 90)

            # Save extracted emails
            self.save_extracted_emails()
            self.update_status("Process completed successfully", 100)

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
            logging.exception("Critical error in email extractor")
            self.update_status(f"Error: {type(e).__name__}: {str(e).splitlines()[0]}", 0)
            raise
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
    print("6. Support target companies (e.g., Google, Microsoft)")
    print("7. Support target countries/locations (e.g., UAE, USA, Canada)")
    print("\nSearch Examples:")
    print("- React js + Hiring + UAE")
    print("- Frontend Developer + Hiring + Google + Microsoft + USA")
    print("- React.js Developer + Hiring + Amazon + UAE + Canada")
    print("\nMake sure you have:")
    print("- Chrome browser installed")
    print("- An uploaded resume selected in the dashboard")
    print("- Valid LinkedIn credentials")
    print("- Configure target companies/countries in temp_job_config.json")
    print("\nExample configuration:")
    print("""
{
  "subject": "Application for React.js Developer Position",
  "search_terms": ["React js Developer", "Frontend Developer"],
  "target_companies": ["Google", "Microsoft", "Amazon", "Meta"],
  "target_countries": ["UAE", "USA", "Canada", "Germany"],
  "date_filter": "past-week"
}
    """)
    print("\nStarting in 5 seconds...")

    time.sleep(5)

    try:
        extractor = LinkedInEmailExtractor()
        extractor.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    if "--check-startup" in sys.argv:
        # Validate imports and local configuration without opening Chrome or sending mail.
        LinkedInEmailExtractor()
        print("Extractor startup check passed")
    else:
        main()
