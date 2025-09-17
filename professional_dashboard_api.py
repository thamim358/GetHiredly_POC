#!/usr/bin/env python3
"""
LinkedIn AutoBot Professional Dashboard API Server
Provides comprehensive REST API endpoints for professional job application automation
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
import zipfile
import tempfile
import csv
import io
import secrets
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Import license manager
try:
    from license_manager import LicenseManager, LicenseValidator
    LICENSE_AVAILABLE = True
except ImportError:
    LICENSE_AVAILABLE = False
    print("⚠️ License manager not available - running without licensing")

# Production configuration and environment detection
# Check multiple ways Railway.app might indicate production
railway_indicators = [
    os.environ.get('RAILWAY_ENVIRONMENT'),
    os.environ.get('RAILWAY_PROJECT_ID'), 
    os.environ.get('PORT'),
    os.environ.get('PRODUCTION')
]

# Set ENVIRONMENT based on Railway indicators
if any(railway_indicators):
    os.environ['ENVIRONMENT'] = 'production'
    ENVIRONMENT = 'production'
else:
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

IS_PRODUCTION = ENVIRONMENT == 'production'

# Log environment detection
print(f"Environment detection: {ENVIRONMENT}")
print(f"Railway indicators: {[i for i in railway_indicators if i]}")
if IS_PRODUCTION:
    print("Running in PRODUCTION mode")
else:
    print("Running in DEVELOPMENT mode")

# Set up logging for production
if IS_PRODUCTION:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
    logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

# Try to import pandas and openpyxl for Excel export
try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning("pandas not available. Excel export will be disabled.")

# Configure logging
if not IS_PRODUCTION:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

# Initialize Flask app with production configuration
app = Flask(__name__)
CORS(app)

# Production security configuration
if IS_PRODUCTION:
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    app.config['DEBUG'] = False
    app.config['ENV'] = 'production'
    logger.info("LinkedIn AutoBot starting in PRODUCTION mode")
else:
    app.config['SECRET_KEY'] = 'dev-secret-key'
    app.config['DEBUG'] = True
    logger.info("LinkedIn AutoBot starting in DEVELOPMENT mode")

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ProfessionalBotController:
    def __init__(self):
        self.email_extractor_process = None
        self.aibot_process = None
        self.start_time = datetime.now()
        self.user_config = {}
        
        # Initialize comprehensive stats
        self.stats = {
            'email_extractor': {
                'status': 'stopped',
                'emails_sent': 0,
                'emails_extracted': 0,
                'posts_processed': 0,
                'start_time': None,
                'runtime': '00:00:00',
                'last_activity': None
            },
            'aibot': {
                'status': 'stopped',
                'applications_submitted': 0,
                'jobs_applied': 0,
                'jobs_external': 0,
                'jobs_failed': 0,
                'success_rate': 0,
                'start_time': None,
                'runtime': '00:00:00',
                'last_activity': None
            },
            'recent_emails': [],
            'recent_applications': [],
            'system': {
                'uptime': '00:00:00',
                'version': '2.0',
                'mode': 'Professional'
            }
        }
        
        # Load existing stats if available
        self._load_persistent_stats()
        
    def save_user_config(self, config_data):
        """Save comprehensive user configuration securely"""
        try:
            # Validate required fields with better error messages
            required_fields = ['personal', 'linkedin', 'job']
            missing_fields = []
            
            for field in required_fields:
                if field not in config_data:
                    missing_fields.append(field)
            
            if missing_fields:
                error_msg = f"Missing required configuration sections: {', '.join(missing_fields)}"
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            # Validate personal data
            personal = config_data.get('personal', {})
            required_personal = ['fullName', 'email', 'phone', 'location']
            missing_personal = [field for field in required_personal if not personal.get(field, '').strip()]
            
            if missing_personal:
                error_msg = f"Missing required personal information: {', '.join(missing_personal)}"
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            # Validate LinkedIn credentials
            linkedin = config_data.get('linkedin', {})
            if not linkedin.get('email', '').strip() or not linkedin.get('password', '').strip():
                error_msg = "LinkedIn email and password are required"
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            # Validate Gmail credentials (optional but recommended)
            gmail = linkedin.get('gmail', {})
            if gmail:  # Only validate if Gmail section is provided
                if not gmail.get('senderEmail', '').strip():
                    error_msg = "Gmail sender email is required when Gmail configuration is provided"
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                if not gmail.get('senderPassword', '').strip():
                    error_msg = "Gmail sender password (app password) is required when Gmail configuration is provided"
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                
                # Validate email format
                sender_email = gmail.get('senderEmail', '').strip()
                if '@' not in sender_email or '.' not in sender_email.split('@')[1]:
                    error_msg = "Invalid Gmail email format"
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                
                logging.info(f"Gmail configuration validated for: {sender_email}")
            else:
                logging.warning("No Gmail configuration provided - email sending may use default credentials")
            
            # Validate job configuration
            job = config_data.get('job', {})
            required_job = ['subject', 'searchTerms', 'emailTemplate', 'botType']
            missing_job = [field for field in required_job if not job.get(field)]
            
            if missing_job:
                error_msg = f"Missing required job configuration: {', '.join(missing_job)}"
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            # Save personal data (non-sensitive)
            personal_config = {
                'personal': config_data.get('personal', {}),
                'job': config_data.get('job', {}),
                'timestamp': datetime.now().isoformat(),
                'version': '2.0'
            }
            
            with open('user_config.json', 'w') as f:
                json.dump(personal_config, f, indent=2)
            
            # Save LinkedIn credentials separately (more secure)
            linkedin_config = config_data.get('linkedin', {})
            # In production, consider encrypting this file
            with open('linkedin_credentials.json', 'w') as f:
                json.dump(linkedin_config, f, indent=2)
            
            # Prepare job configuration for bot processes
            job_config = self._prepare_job_config(config_data)
            
            with open('temp_job_config.json', 'w') as f:
                json.dump(job_config, f, indent=2)
            
            self.user_config = config_data
            logging.info("User configuration saved successfully")
            return True
            
        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logging.error(f"Error saving user config: {e}")
            raise ValueError(f"Failed to save configuration: {str(e)}")
    
    
    def _prepare_job_config(self, config_data):
        """Prepare job configuration with placeholder replacement"""
        personal = config_data.get('personal', {})
        job = config_data.get('job', {})
        
        # Create job config
        job_config = {
            'subject': job.get('subject', ''),
            'search_terms': job.get('searchTerms', []),
            'email_body': job.get('emailTemplate', ''),
            'resume_file': 'uploaded_resume.pdf',  # Standard name for uploaded resume
            'bot_type': job.get('botType', 'email'),
            'job_role': job.get('role', 'custom'),
            'custom_title': job.get('customTitle', ''),
            'date_filter': job.get('dateFilter', 'past-week'),  # Add date filter preference
            'emails_per_hour': job.get('emailsPerHour', '20'),
            'daily_limit': job.get('dailyLimit', '100'),
            'skip_weekends': job.get('skipWeekends', False),
            'companyFilter': job.get('companyFilter', {'enabled': False, 'companies': []}),  # Add company filter
            'countryFilter': job.get('countryFilter', {'enabled': False, 'countries': []}),  # Add country filter
            'user_info': {
                'name': personal.get('fullName', ''),
                'email': personal.get('email', ''),
                'phone': personal.get('phone', ''),
                'location': personal.get('location', ''),
                'website': personal.get('website', '')
            }
        }
        
        # Replace placeholders in email template
        email_body = job_config['email_body']
        placeholders = {
            '[FULL_NAME]': personal.get('fullName', ''),
            '[EMAIL]': personal.get('email', ''),
            '[PHONE]': personal.get('phone', ''),
            '[WEBSITE]': personal.get('website', ''),
            '[LOCATION]': personal.get('location', '')
        }
        
        for placeholder, value in placeholders.items():
            email_body = email_body.replace(placeholder, value)
        
        job_config['email_body'] = email_body
        
        # Log filter configuration for debugging
        company_filter = job_config.get('companyFilter', {})
        country_filter = job_config.get('countryFilter', {})
        
        logging.info(f"Job config prepared:")
        logging.info(f"  Company Filter: {'Enabled' if company_filter.get('enabled') else 'Disabled'}")
        if company_filter.get('enabled') and company_filter.get('companies'):
            company_names = [comp.get('name', 'Unknown') for comp in company_filter.get('companies', [])]
            logging.info(f"  Target Companies: {', '.join(company_names[:3])}" + (f" (+{len(company_names)-3} more)" if len(company_names) > 3 else ""))
        
        logging.info(f"  Country Filter: {'Enabled' if country_filter.get('enabled') else 'Disabled'}")
        if country_filter.get('enabled') and country_filter.get('countries'):
            country_names = [country.get('name', 'Unknown') for country in country_filter.get('countries', [])]
            logging.info(f"  Target Countries: {', '.join(country_names[:3])}" + (f" (+{len(country_names)-3} more)" if len(country_names) > 3 else ""))
            # Show search terms for debugging
            for country in country_filter.get('countries', []):
                logging.info(f"  {country.get('name', 'Unknown')} -> Search terms: '{country.get('searchTerms', 'No search terms')}'")
        
        return job_config
    
    def start_email_extractor(self, user_data=None):
        """Start the LinkedIn email extractor with comprehensive configuration"""
        try:
            if self.email_extractor_process and self.email_extractor_process.poll() is None:
                return {'success': False, 'error': 'Email extractor is already running'}
            
            # Save user configuration if provided
            if user_data:
                try:
                    self.save_user_config(user_data)
                except ValueError as e:
                    return {'success': False, 'error': str(e)}
            
            # Check if configuration exists
            if not os.path.exists('temp_job_config.json'):
                return {'success': False, 'error': 'No job configuration found. Please complete setup first.'}
            
            # Set up environment for portable mode
            env = os.environ.copy()
            if os.environ.get('LINKEDIN_AUTOBOT_PORTABLE') == '1':
                env['LINKEDIN_AUTOBOT_PORTABLE'] = '1'
                logging.info("Starting email extractor in portable mode")
            
            # Start the email extractor process
            self.email_extractor_process = subprocess.Popen([
                sys.executable, 'linkedin_email_extractor.py'
            ], cwd=os.getcwd(), env=env, 
               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            self.stats['email_extractor']['status'] = 'running'
            self.stats['email_extractor']['start_time'] = datetime.now()
            self.stats['email_extractor']['last_activity'] = datetime.now()
            
            # Wait to check if process started successfully
            time.sleep(5)  # Give more time for startup
            poll_result = self.email_extractor_process.poll()
            
            if poll_result is not None:
                # Process ended, get error output
                stdout, stderr = self.email_extractor_process.communicate(timeout=5)
                error_msg = f"Email extractor failed to start (return code: {poll_result})"
                if stderr:
                    error_msg += f" - Error: {stderr.strip()}"
                if stdout:
                    error_msg += f" - Output: {stdout.strip()}"
                    
                logging.error(error_msg)
                self.stats['email_extractor']['status'] = 'error'
                return {'success': False, 'error': error_msg}
            
            logging.info("Email extractor started successfully")
            
            # Start monitoring thread
            threading.Thread(target=self._monitor_email_extractor, daemon=True).start()
            
            return {'success': True, 'message': 'Email extractor started successfully'}
            
        except Exception as e:
            logging.error(f"Error starting email extractor: {e}")
            self.stats['email_extractor']['status'] = 'error'
            return {'success': False, 'error': str(e)}
    
    def start_aibot(self, user_data=None):
        """Start the AI job application bot"""
        try:
            if self.aibot_process and self.aibot_process.poll() is None:
                return {'success': False, 'error': 'AI bot is already running'}
            
            # Save user configuration if provided
            if user_data:
                try:
                    self.save_user_config(user_data)
                except ValueError as e:
                    return {'success': False, 'error': str(e)}
            
            # Check if configuration exists
            if not os.path.exists('user_config.json'):
                return {'success': False, 'error': 'No user configuration found. Please complete setup first.'}
            
            # Set up environment for portable mode
            env = os.environ.copy()
            if os.environ.get('LINKEDIN_AUTOBOT_PORTABLE') == '1':
                env['LINKEDIN_AUTOBOT_PORTABLE'] = '1'
                logging.info("Starting AI bot in portable mode")
            
            # Start the AI bot process
            self.aibot_process = subprocess.Popen([
                sys.executable, 'runAiBot.py'
            ], cwd=os.getcwd(), env=env,
               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            self.stats['aibot']['status'] = 'running'
            self.stats['aibot']['start_time'] = datetime.now()
            self.stats['aibot']['last_activity'] = datetime.now()
            
            # Reset stats for new session (keep historical data until new applications are made)
            # Don't reset the counters immediately - they'll be updated from actual data files
            logging.info("AI bot started - stats will update from application files")
            
            # Wait to check if process started successfully
            time.sleep(5)  # Give more time for startup
            poll_result = self.aibot_process.poll()
            
            if poll_result is not None:
                # Process ended, get error output
                stdout, stderr = self.aibot_process.communicate(timeout=5)
                error_msg = f"AI bot failed to start (return code: {poll_result})"
                if stderr:
                    error_msg += f" - Error: {stderr.strip()}"
                if stdout:
                    error_msg += f" - Output: {stdout.strip()}"
                    
                logging.error(error_msg)
                self.stats['aibot']['status'] = 'error'
                return {'success': False, 'error': error_msg}
            
            logging.info("AI bot started successfully")
            
            # Start monitoring thread
            threading.Thread(target=self._monitor_aibot, daemon=True).start()
            
            return {'success': True, 'message': 'AI bot started successfully'}
            
        except Exception as e:
            logging.error(f"Error starting AI bot: {e}")
            self.stats['aibot']['status'] = 'error'
            return {'success': False, 'error': str(e)}
    
    def stop_bot(self):
        """Stop all running bots"""
        try:
            stopped = []
            
            if self.email_extractor_process and self.email_extractor_process.poll() is None:
                self.email_extractor_process.terminate()
                try:
                    self.email_extractor_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.email_extractor_process.kill()
                stopped.append('Email Extractor')
                self.stats['email_extractor']['status'] = 'stopped'
            
            if self.aibot_process and self.aibot_process.poll() is None:
                self.aibot_process.terminate()
                try:
                    self.aibot_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.aibot_process.kill()
                stopped.append('AI Bot')
                self.stats['aibot']['status'] = 'stopped'
            
            message = f"Stopped: {', '.join(stopped)}" if stopped else "No bots were running"
            logging.info(message)
            
            return {'success': True, 'message': message}
            
        except Exception as e:
            logging.error(f"Error stopping bots: {e}")
            return {'success': False, 'error': str(e)}
    
    def _monitor_email_extractor(self):
        """Monitor the email extractor process and update stats"""
        while self.email_extractor_process and self.email_extractor_process.poll() is None:
            try:
                self._update_email_stats()
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error monitoring email extractor: {e}")
                break
        
        # Process ended
        self.stats['email_extractor']['status'] = 'stopped'
        self.email_extractor_process = None
        logging.info("Email extractor monitoring stopped")
    
    def _monitor_aibot(self):
        """Monitor the AI bot process and update stats"""
        while self.aibot_process and self.aibot_process.poll() is None:
            try:
                self._update_aibot_stats()
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error monitoring AI bot: {e}")
                break
        
        # Process ended
        self.stats['aibot']['status'] = 'stopped'
        self.aibot_process = None
        logging.info("AI bot monitoring stopped")
    
    def _update_email_stats(self):
        """Update email extractor statistics from various sources"""
        try:
            # Update runtime
            if self.stats['email_extractor']['start_time']:
                runtime = datetime.now() - self.stats['email_extractor']['start_time']
                self.stats['email_extractor']['runtime'] = str(runtime).split('.')[0]
            
            # Read detailed status from extractor status file
            if os.path.exists('extractor_status.json'):
                try:
                    with open('extractor_status.json', 'r') as f:
                        status_data = json.load(f)
                        self.stats['email_extractor']['detailed_status'] = status_data.get('status', 'Running')
                        self.stats['email_extractor']['progress'] = status_data.get('progress', 0)
                        self.stats['email_extractor']['last_activity'] = datetime.now()
                except Exception as e:
                    logging.error(f"Error reading extractor status: {e}")
            
            # Read from sent emails log
            if os.path.exists('sent_emails_log.csv'):
                with open('sent_emails_log.csv', 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    if len(lines) > 1:  # Has header
                        self.stats['email_extractor']['emails_sent'] = len(lines) - 1
                        
                        # Update recent emails
                        recent_emails = []
                        for line in lines[-6:]:  # Last 5 emails plus header
                            if line.strip() and ',' in line and line != lines[0]:  # Skip header
                                parts = line.strip().split(',')
                                if len(parts) >= 2:
                                    recent_emails.append({
                                        'email': parts[0],
                                        'status': 'sent',
                                        'time': parts[1] if len(parts) > 1 else 'Unknown'
                                    })
                        self.stats['recent_emails'] = recent_emails
            
            # Read from extracted emails JSON
            if os.path.exists('extracted_emails.json'):
                with open('extracted_emails.json', 'r') as f:
                    data = json.load(f)
                    self.stats['email_extractor']['emails_extracted'] = data.get('total_count', 0)
                    self.stats['email_extractor']['posts_processed'] = data.get('posts_processed', 0)
            
            self.stats['email_extractor']['last_activity'] = datetime.now()
            
        except Exception as e:
            logging.error(f"Error updating email stats: {e}")
    
    def _update_aibot_stats(self):
        """Update AI bot statistics from log files"""
        try:
            # Update runtime
            if self.stats['aibot']['start_time']:
                runtime = datetime.now() - self.stats['aibot']['start_time']
                self.stats['aibot']['runtime'] = str(runtime).split('.')[0]
            
            # Read from application history files
            applied_count = 0
            failed_count = 0
            
            # Check applied applications - try multiple possible paths
            applied_files = [
                'all excels/all_applied_applications_history.csv',
                'all_applied_applications_history.csv',
                'logs/applied_applications.csv'
            ]
            
            for file_path in applied_files:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            if len(lines) > 1:  # Exclude header
                                applied_count = len(lines) - 1
                        logging.info(f"Found applied applications file: {file_path} with {applied_count} applications")
                        break
                    except Exception as e:
                        logging.warning(f"Error reading {file_path}: {e}")
            
            # Check failed applications - try multiple possible paths
            failed_files = [
                'all excels/all_failed_applications_history.csv',
                'all_failed_applications_history.csv',
                'logs/failed_applications.csv'
            ]
            
            for file_path in failed_files:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            if len(lines) > 1:  # Exclude header
                                failed_count = len(lines) - 1
                        logging.info(f"Found failed applications file: {file_path} with {failed_count} applications")
                        break
                    except Exception as e:
                        logging.warning(f"Error reading {file_path}: {e}")
            
            # Only update stats if the bot is actually running or has data
            if self.stats['aibot']['status'] == 'running' or applied_count > 0 or failed_count > 0:
                self.stats['aibot']['jobs_applied'] = applied_count
                self.stats['aibot']['jobs_failed'] = failed_count
                self.stats['aibot']['applications_submitted'] = applied_count
                
                # Calculate success rate
                total_attempts = applied_count + failed_count
                if total_attempts > 0:
                    self.stats['aibot']['success_rate'] = round((applied_count / total_attempts) * 100, 1)
                else:
                    self.stats['aibot']['success_rate'] = 0
                
                self.stats['aibot']['last_activity'] = datetime.now()
                logging.debug(f"Updated AI bot stats: {applied_count} applied, {failed_count} failed")
            else:
                # Bot is stopped and no data files found - reset dynamic stats but keep historical count
                if applied_count == 0 and failed_count == 0:
                    logging.debug("AI bot stopped and no application files found - keeping last known stats")
            
        except Exception as e:
            logging.error(f"Error updating AI bot stats: {e}")
    
    def _load_persistent_stats(self):
        """Load persistent statistics if available"""
        try:
            if os.path.exists('bot_stats.json'):
                with open('bot_stats.json', 'r') as f:
                    saved_stats = json.load(f)
                    # Merge with current stats, keeping current status
                    for bot_type in ['email_extractor', 'aibot']:
                        if bot_type in saved_stats:
                            for key, value in saved_stats[bot_type].items():
                                if key not in ['status', 'start_time']:  # Don't overwrite these
                                    self.stats[bot_type][key] = value
        except Exception as e:
            logging.error(f"Error loading persistent stats: {e}")
    
    def save_persistent_stats(self):
        """Save current statistics to persistent storage"""
        try:
            with open('bot_stats.json', 'w') as f:
                json.dump(self.stats, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Error saving persistent stats: {e}")
    
    def get_stats(self):
        """Get comprehensive current statistics"""
        # Update system uptime
        uptime = datetime.now() - self.start_time
        self.stats['system']['uptime'] = str(uptime).split('.')[0]
        
        # Update stats from files
        if self.stats['email_extractor']['status'] == 'running':
            self._update_email_stats()
        if self.stats['aibot']['status'] == 'running':
            self._update_aibot_stats()
        
        return self.stats
    
    def export_data(self):
        """Export all application data as a ZIP file"""
        try:
            # Create temporary zip file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add configuration files
                    files_to_export = [
                        'user_config.json',
                        'sent_emails_log.csv',
                        'extracted_emails.json',
                        'bot_stats.json'
                    ]
                    
                    for filename in files_to_export:
                        if os.path.exists(filename):
                            zipf.write(filename)
                    
                    # Add Excel files
                    excel_dir = 'all excels'
                    if os.path.exists(excel_dir):
                        for root, dirs, files in os.walk(excel_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, '.')
                                zipf.write(file_path, arcname)
                    
                    # Add logs
                    logs_dir = 'logs'
                    if os.path.exists(logs_dir):
                        for root, dirs, files in os.walk(logs_dir):
                            for file in files:
                                if file.endswith(('.txt', '.log')):
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, '.')
                                    zipf.write(file_path, arcname)
                
                return tmp_file.name
                
        except Exception as e:
            logging.error(f"Error creating export: {e}")
            return None

# Initialize bot controller
bot_controller = ProfessionalBotController()

# Routes
@app.route('/')
def landing():
    """Serve the landing page"""
    return render_template('landing.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Railway.app"""
    return jsonify({
        'status': 'healthy',
        'environment': ENVIRONMENT,
        'timestamp': datetime.now().isoformat(),
        'service': 'LinkedIn AutoBot Professional Dashboard'
    })

@app.route('/test-webdriver')
def test_webdriver():
    """Test WebDriver functionality for debugging"""
    try:
        if IS_PRODUCTION:
            from production_webdriver import create_production_chrome_driver
            driver = create_production_chrome_driver()
            
            # Test basic functionality
            driver.get("https://www.google.com")
            title = driver.title
            user_agent = driver.execute_script("return navigator.userAgent")
            webdriver_property = driver.execute_script("return navigator.webdriver")
            driver.quit()
            
            return jsonify({
                'status': 'success',
                'environment': 'production',
                'title': title,
                'user_agent': user_agent,
                'webdriver_detected': webdriver_property,
                'headless_mode': False,  # We're using virtual display, not headless
                'message': 'Production WebDriver working with virtual display (non-headless)'
            })
        else:
            return jsonify({
                'status': 'skipped',
                'environment': 'development',
                'message': 'WebDriver test only runs in production'
            })
    except Exception as e:
        logger.error(f"WebDriver test failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'environment': ENVIRONMENT,
            'error': str(e),
            'message': 'WebDriver test failed'
        }), 500

@app.route('/dashboard')
@app.route('/professional-dashboard')
def dashboard():
    """Serve the professional dashboard"""
    return render_template('professional_index.html')

@app.route('/api/stats')
def get_stats():
    """Get current bot statistics"""
    try:
        stats = bot_controller.get_stats()
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Error in get_stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start-email-extractor', methods=['POST'])
def start_email_extractor():
    """Start the email extractor with user configuration"""
    try:
        user_data = request.json
        
        if not user_data:
            return jsonify({'success': False, 'error': 'No configuration data provided'}), 400
        
        logging.info(f"Starting email extractor with user data")
        
        result = bot_controller.start_email_extractor(user_data)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except ValueError as e:
        # Validation errors
        logging.error(f"Validation error in start_email_extractor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error in start_email_extractor endpoint: {e}")
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/start-aibot', methods=['POST'])
def start_aibot():
    """Start the AI bot with user configuration"""
    try:
        user_data = request.json
        
        if not user_data:
            return jsonify({'success': False, 'error': 'No configuration data provided'}), 400
        
        logging.info(f"Starting AI bot with user data")
        
        result = bot_controller.start_aibot(user_data)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except ValueError as e:
        # Validation errors
        logging.error(f"Validation error in start_aibot: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error in start_aibot endpoint: {e}")
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/stop-bot', methods=['POST'])
def stop_bot():
    """Stop all running bots"""
    try:
        result = bot_controller.stop_bot()
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error in stop_bot endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reset-aibot-stats', methods=['POST'])
def reset_aibot_stats():
    """Reset AI bot statistics to start fresh"""
    try:
        bot_controller.stats['aibot']['applications_submitted'] = 0
        bot_controller.stats['aibot']['jobs_applied'] = 0
        bot_controller.stats['aibot']['jobs_failed'] = 0
        bot_controller.stats['aibot']['success_rate'] = 0
        bot_controller.stats['aibot']['start_time'] = None
        bot_controller.stats['aibot']['runtime'] = "0:00:00"
        bot_controller.stats['aibot']['last_activity'] = None
        
        logging.info("AI bot statistics reset")
        return jsonify({'success': True, 'message': 'AI bot statistics reset successfully'})
    except Exception as e:
        logging.error(f"Error resetting AI bot stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    """Handle resume file upload"""
    try:
        if 'resume' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                return jsonify({'success': False, 'error': 'File too large (max 10MB)'}), 400
            
            # Save file with secure name
            filename = 'thamim_resume.pdf'  # Standard name
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            logging.info(f"Resume uploaded successfully: {filename}")
            return jsonify({
                'success': True, 
                'message': 'Resume uploaded successfully',
                'filename': filename
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
            
    except Exception as e:
        logging.error(f"Error uploading resume: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-data')
def export_data():
    """Export all application data"""
    try:
        zip_path = bot_controller.export_data()
        if zip_path:
            def remove_file(response):
                try:
                    os.unlink(zip_path)
                except Exception as e:
                    logging.error(f"Error removing temp file: {e}")
                return response
            
            filename = f"linkedin-autobot-data-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
            response = send_file(zip_path, as_attachment=True, download_name=filename)
            response.call_on_close(lambda: os.unlink(zip_path))
            return response
        else:
            return jsonify({'error': 'Failed to create export'}), 500
            
    except Exception as e:
        logging.error(f"Error in export_data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-config', methods=['POST'])
def save_config():
    """Save user configuration"""
    try:
        config_data = request.json
        success = bot_controller.save_user_config(config_data)
        
        if success:
            return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save configuration'}), 500
            
    except Exception as e:
        logging.error(f"Error saving config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/load-config')
def load_config():
    """Load saved user configuration"""
    try:
        config = {}
        
        if os.path.exists('user_config.json'):
            with open('user_config.json', 'r') as f:
                config = json.load(f)
        
        return jsonify({'success': True, 'config': config})
        
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history')
def get_application_history():
    """Get application history from CSV files"""
    try:
        applications = []
        
        # Read from sent_emails_log.csv (the actual file with data)
        sent_emails_file = 'sent_emails_log.csv'
        if os.path.exists(sent_emails_file):
            try:
                with open(sent_emails_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        # Extract company from email domain
                        email = row.get('email', '')
                        company = ''
                        if email:
                            domain = email.split('@')[1] if '@' in email else ''
                            company = domain.split('.')[0].title() if domain else 'Unknown'
                        
                        # Extract position from subject
                        subject = row.get('subject', '')
                        position = ''
                        if 'React.js Developer' in subject:
                            position = 'React.js Developer'
                        elif 'UI Developer' in subject:
                            position = 'UI Developer'
                        elif 'Web Developer' in subject:
                            position = 'Web Developer'
                        elif 'Frontend Developer' in subject:
                            position = 'Frontend Developer'
                        elif 'Full Stack Developer' in subject:
                            position = 'Full Stack Developer'
                        else:
                            position = 'Developer'
                        
                        applications.append({
                            'id': f"sent_{i}",
                            'date': row.get('date_sent', ''),
                            'company': company,
                            'position': position,
                            'email': email,
                            'status': 'success',  # Assume sent emails are successful
                            'source': 'LinkedIn Email Extractor',
                            'subject': subject,
                            'location': 'N/A'
                        })
            except Exception as e:
                logging.error(f"Error reading sent_emails_log.csv: {e}")
        
        # Also read successful applications from excel folder if exists
        success_file = 'all excels/all_applied_applications_history.csv'
        if os.path.exists(success_file):
            try:
                with open(success_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        applications.append({
                            'id': f"success_{len(applications)}",
                            'date': row.get('Date', ''),
                            'company': row.get('Company', ''),
                            'position': row.get('Position', ''),
                            'email': row.get('Email', ''),
                            'status': 'success',
                            'source': 'LinkedIn AI Bot',
                            'subject': row.get('Subject', ''),
                            'location': row.get('Location', '')
                        })
            except Exception as e:
                logging.error(f"Error reading success file: {e}")
        
        # Read failed applications
        failed_file = 'all excels/all_failed_applications_history.csv'
        if os.path.exists(failed_file):
            try:
                with open(failed_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        applications.append({
                            'id': f"failed_{len(applications)}",
                            'date': row.get('Date', ''),
                            'company': row.get('Company', ''),
                            'position': row.get('Position', ''),
                            'email': row.get('Email', ''),
                            'status': 'failed',
                            'source': 'LinkedIn AI Bot',
                            'error': row.get('Error', ''),
                            'location': row.get('Location', '')
                        })
            except Exception as e:
                logging.error(f"Error reading failed file: {e}")
        
        # Sort by date (newest first)
        applications.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return jsonify({
            'success': True, 
            'applications': applications,
            'total': len(applications)
        })
        
    except Exception as e:
        logging.error(f"Error getting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/excel', methods=['POST'])
def export_excel():
    """Export application data to Excel format"""
    try:
        if not EXCEL_AVAILABLE:
            return jsonify({'success': False, 'error': 'Excel export not available. Please install pandas and openpyxl.'}), 400
        
        data = request.json.get('data', [])
        
        if not data:
            return jsonify({'success': False, 'error': 'No data to export'}), 400
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Applications', index=False)
            
            # Add summary sheet
            summary_data = {
                'Metric': ['Total Applications', 'Successful', 'Failed', 'Success Rate'],
                'Value': [
                    len(data),
                    len([app for app in data if app.get('status') == 'success']),
                    len([app for app in data if app.get('status') == 'failed']),
                    f"{(len([app for app in data if app.get('status') == 'success']) / len(data) * 100):.1f}%" if data else "0%"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        output.seek(0)
        
        filename = f"linkedin_applications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return Response(
            output.getvalue(),
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    except Exception as e:
        logging.error(f"Error exporting Excel: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    """Export application data to CSV format"""
    try:
        data = request.json.get('data', [])
        
        if not data:
            return jsonify({'success': False, 'error': 'No data to export'}), 400
        
        # Create CSV in memory
        output = io.StringIO()
        
        if data:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        # Convert to bytes for response
        csv_bytes = io.BytesIO()
        csv_bytes.write(output.getvalue().encode('utf-8'))
        csv_bytes.seek(0)
        
        filename = f"linkedin_applications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            csv_bytes.getvalue(),
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv'
            }
        )
        
    except Exception as e:
        logging.error(f"Error exporting CSV: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Cleanup on shutdown
@app.teardown_appcontext
def cleanup(error):
    try:
        bot_controller.save_persistent_stats()
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

if __name__ == '__main__':
    try:
        print("=" * 60)
        print("LinkedIn AutoBot Professional Dashboard")
        print("=" * 60)
        print(f"Dashboard URL: http://localhost:5000")
        print(f"API Base URL: http://localhost:5000/api")
        print("=" * 60)
        print()
        print("Features:")
        print("Complete user configuration")
        print("Resume upload & management")
        print("Job role templates")
        print("Email & AI bot automation")
        print("Real-time statistics")
        print("Data export capabilities")
        print("Professional UI design")
        print()
        
        # Check if running in portable mode
        is_portable = os.environ.get('LINKEDIN_AUTOBOT_PORTABLE') == '1'
        if is_portable:
            print("PORTABLE MODE DETECTED")
            print("Chrome browser embedded")
            print("ChromeDriver embedded")
            print("No installation required")
            print()
        
        # Production vs Development configuration
        if IS_PRODUCTION:
            port = int(os.environ.get('PORT', 5000))
            host = '0.0.0.0'
            debug = False
            print(f"Starting PRODUCTION server on {host}:{port}")
        else:
            # Try different ports if 5000 is in use
            ports_to_try = [5000, 5001, 5002, 5003, 8000, 8080]
            port = None
            host = '127.0.0.1'  # Use localhost instead of 0.0.0.0 for dev
            debug = True
            
            for try_port in ports_to_try:
                try:
                    # Test if port is available
                    import socket
                    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    test_socket.bind((host, try_port))
                    test_socket.close()
                    port = try_port
                    break
                except socket.error:
                    continue
            
            if port is None:
                print("No available ports found. Trying default 5000...")
                port = 5000
            
            print(f"Starting DEVELOPMENT server on {host}:{port}")
        
        app.run(host=host, port=port, debug=debug, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        bot_controller.stop_bot()
        print("Server stopped.")
    except Exception as e:
        logging.error(f"Error starting server: {e}")
        print(f"Failed to start server: {e}")
        print("\nTroubleshooting:")
        print("1. Close any other instances of LinkedInAutoBot")
        print("2. Check if port 5000 is already in use")
        print("3. Try running as administrator")
        input("\nPress Enter to exit...")
