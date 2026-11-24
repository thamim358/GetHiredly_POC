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
import uuid
import shutil
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file, Response, redirect, url_for
from werkzeug.utils import secure_filename
from role_campaign import campaign_roles, resume_path
from email_formatting import personalize_email_template, render_email_html
from linkedin_networking import NetworkingAssistant

# Windows consoles often use cp1252 and crash on Unicode emojis in print statements.
# Force UTF-8 output so the startup banner and logs never kill the server.
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Try to import pandas and openpyxl for Excel export
try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("Warning: pandas not available. Excel export will be disabled.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def merge_linkedin_credentials(incoming, saved):
    """Keep locally saved passwords when a dashboard form leaves them blank."""
    incoming = incoming if isinstance(incoming, dict) else {}
    saved = saved if isinstance(saved, dict) else {}
    merged = {key: incoming.get(key) or saved.get(key, '') for key in ('email', 'password', 'profile')}
    new_gmail = incoming.get('gmail') if isinstance(incoming.get('gmail'), dict) else {}
    old_gmail = saved.get('gmail') if isinstance(saved.get('gmail'), dict) else {}
    gmail = {key: new_gmail.get(key) or old_gmail.get(key, '') for key in ('senderEmail', 'senderPassword')}
    if any(gmail.values()):
        merged['gmail'] = gmail
    return merged

class ProfessionalBotController:
    def __init__(self):
        self.email_extractor_process = None
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
            'recent_emails': [],
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

            # Validate LinkedIn credentials; the dashboard never reloads saved passwords.
            saved_linkedin = {}
            if os.path.exists('linkedin_credentials.json'):
                with open('linkedin_credentials.json', encoding='utf-8') as source:
                    saved_linkedin = json.load(source)
            linkedin = merge_linkedin_credentials(config_data.get('linkedin'), saved_linkedin)
            config_data = dict(config_data)
            config_data['linkedin'] = linkedin
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
            required_job = ['botType']
            missing_job = [field for field in required_job if not job.get(field)]

            if missing_job:
                error_msg = f"Missing required job configuration: {', '.join(missing_job)}"
                logging.error(error_msg)
                raise ValueError(error_msg)
            roles = campaign_roles(job)

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
        roles = campaign_roles(job)

        # Create job config
        job_config = {
            'subject': roles[0]['subject'],
            'search_terms': roles[0]['search_terms'],
            'email_body': roles[0]['email_body'],
            'resume_file': roles[0]['resume_file'],
            'roles': roles,
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

        for role in job_config['roles']:
            role['email_body'] = personalize_email_template(role['email_body'], personal)
        job_config['email_body'] = job_config['roles'][0]['email_body']

        # Log filter configuration for debugging
        company_filter = job_config.get('companyFilter', {})
        country_filter = job_config.get('countryFilter', {})

        logging.info(f"📋 Job config prepared:")
        logging.info(f"  🏢 Company Filter: {'Enabled' if company_filter.get('enabled') else 'Disabled'}")
        if company_filter.get('enabled') and company_filter.get('companies'):
            company_names = [comp.get('name', 'Unknown') for comp in company_filter.get('companies', [])]
            logging.info(f"  🏢 Target Companies: {', '.join(company_names[:3])}" + (f" (+{len(company_names)-3} more)" if len(company_names) > 3 else ""))

        logging.info(f"  🌍 Country Filter: {'Enabled' if country_filter.get('enabled') else 'Disabled'}")
        if country_filter.get('enabled') and country_filter.get('countries'):
            country_names = [country.get('name', 'Unknown') for country in country_filter.get('countries', [])]
            logging.info(f"  🌍 Target Countries: {', '.join(country_names[:3])}" + (f" (+{len(country_names)-3} more)" if len(country_names) > 3 else ""))
            # Show search terms for debugging
            for country in country_filter.get('countries', []):
                logging.info(f"  🌍 {country.get('name', 'Unknown')} -> Search terms: '{country.get('searchTerms', 'No search terms')}'")

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

            # Check startup in the same interpreter before launching browser automation.
            app_directory = os.path.dirname(os.path.abspath(__file__))
            startup_log = os.path.join(app_directory, 'email_extractor_startup.log')
            with open(startup_log, 'a', encoding='utf-8') as output:
                output.write(f"\n--- Extractor startup {datetime.now().isoformat()} ---\n")
                output.flush()
                check = subprocess.run(
                    [sys.executable, 'linkedin_email_extractor.py', '--check-startup'],
                    cwd=app_directory, stdout=output, stderr=subprocess.STDOUT,
                    timeout=20, check=False,
                )
                if check.returncode != 0:
                    code = check.returncode & 0xFFFFFFFF
                    detail = "Windows DLL initialization failed" if code == 0xC0000142 else "Startup check failed"
                    self.stats['email_extractor']['status'] = 'error'
                    self.stats['email_extractor']['detailed_status'] = detail
                    return {'success': False, 'error': f'{detail} (0x{code:08X}). See email_extractor_startup.log.'}

                self.email_extractor_process = subprocess.Popen(
                    [sys.executable, 'linkedin_email_extractor.py'],
                    cwd=app_directory, stdout=output, stderr=subprocess.STDOUT,
                )

            self.stats['email_extractor']['status'] = 'running'
            self.stats['email_extractor']['detailed_status'] = 'Starting email extractor...'
            self.stats['email_extractor']['progress'] = 0
            self.stats['email_extractor']['start_time'] = datetime.now()
            self.stats['email_extractor']['last_activity'] = datetime.now()

            # Wait to check if process started successfully
            time.sleep(3)
            if self.email_extractor_process.poll() is not None:
                code = self.email_extractor_process.returncode & 0xFFFFFFFF
                detail = "Windows DLL initialization failed" if code == 0xC0000142 else "Extractor exited during startup"
                error_msg = f"{detail} (0x{code:08X}). See email_extractor_startup.log."
                logging.error(error_msg)
                self.stats['email_extractor']['status'] = 'error'
                self.stats['email_extractor']['detailed_status'] = detail
                return {'success': False, 'error': error_msg}

            logging.info("Email extractor started successfully")

            # Start monitoring thread
            threading.Thread(target=self._monitor_email_extractor, daemon=True).start()

            return {'success': True, 'message': 'Email extractor started successfully'}

        except Exception as e:
            logging.error(f"Error starting email extractor: {e}")
            self.stats['email_extractor']['status'] = 'error'
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

        # Preserve failures so the dashboard does not keep showing an old
        # "Setting up browser" progress message after the process exits.
        exit_code = self.email_extractor_process.poll() if self.email_extractor_process else None
        stopped_by_user = self.stats['email_extractor']['status'] == 'stopped'
        self.stats['email_extractor']['status'] = (
            'error' if exit_code not in (None, 0) and not stopped_by_user else 'stopped'
        )
        if self.stats['email_extractor']['status'] == 'error':
            self._update_email_stats()
            logging.error("Email extractor exited with code %s", exit_code)
        self.email_extractor_process = None
        logging.info("Email extractor monitoring stopped")

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
                        status_time = datetime.fromisoformat(status_data['timestamp']) if status_data.get('timestamp') else None
                        started_at = self.stats['email_extractor']['start_time']
                        if not started_at or (status_time and status_time >= started_at):
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

    def _load_persistent_stats(self):
        """Load persistent statistics if available"""
        try:
            if os.path.exists('bot_stats.json'):
                with open('bot_stats.json', 'r') as f:
                    saved_stats = json.load(f)
                    # Merge with current stats, keeping current status
                    for bot_type in ['email_extractor']:
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
networking_assistant = NetworkingAssistant()

# Routes
@app.route('/')
def landing():
    """Open the professional dashboard directly."""
    return redirect(url_for('dashboard'))

@app.route('/professional-dashboard')
@app.route('/dashboard')
def dashboard():
    """Serve the professional dashboard"""
    return render_template('professional_index.html')

@app.route('/api/format-email', methods=['POST'])
def format_email_preview():
    """Use the same renderer for preview and outgoing mail."""
    data = request.get_json(silent=True) or {}
    template = data.get('template', '')
    if not isinstance(template, str):
        return jsonify({'error': 'Template must be text'}), 400
    personal = data.get('personal', {})
    if not isinstance(personal, dict):
        return jsonify({'error': 'Personal details must be an object'}), 400
    return jsonify({'html': render_email_html(personalize_email_template(template, personal))})

@app.route('/api/network/search', methods=['POST'])
def start_network_search():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Search settings must be an object'}), 400
    credentials = data.get('linkedin') or {}
    if not credentials and os.path.exists('linkedin_credentials.json'):
        with open('linkedin_credentials.json', encoding='utf-8') as source:
            credentials = json.load(source)
    if not isinstance(credentials, dict):
        return jsonify({'error': 'LinkedIn credentials must be an object'}), 400
    try:
        return jsonify(networking_assistant.start(data, credentials)), 202
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

@app.route('/api/network/state')
def network_search_state():
    return jsonify(networking_assistant.state())

@app.route('/api/network/send-note', methods=['POST'])
def send_network_note():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invitation settings must be an object'}), 400
    try:
        return jsonify(networking_assistant.send(str(data.get('candidateId', '')), str(data.get('note', ''))))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

@app.route('/api/network/send-batch', methods=['POST'])
def send_network_note_batch():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not isinstance(data.get('notes', {}), dict):
        return jsonify({'error': 'Reviewed notes must be provided as an object'}), 400
    try:
        return jsonify(networking_assistant.send_all(data.get('notes', {}))), 202
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

@app.route('/api/network/stop', methods=['POST'])
def stop_network_search():
    networking_assistant.stop()
    return jsonify(networking_assistant.state())

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

@app.route('/api/stop-bot', methods=['POST'])
def stop_bot():
    """Stop all running bots"""
    try:
        result = bot_controller.stop_bot()
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error in stop_bot endpoint: {e}")
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

            # Campaign snapshots get distinct names; legacy single-role upload keeps its name.
            filename = f"role_{uuid.uuid4().hex}.{file.filename.rsplit('.', 1)[1].lower()}" if request.form.get('snapshot') == '1' else f"uploaded_resume.{file.filename.rsplit('.', 1)[1].lower()}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            logging.info(f"Resume uploaded successfully: {filename}")
            return jsonify({
                'success': True,
                'message': 'Resume uploaded successfully',
                'filename': filename,
                'path': f'uploads/{filename}'
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

    except Exception as e:
        logging.error(f"Error uploading resume: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/snapshot-resume', methods=['POST'])
def snapshot_resume():
    """Make a stable copy of an already uploaded resume for one campaign role."""
    try:
        source = resume_path((request.get_json(silent=True) or {}).get('path'))
        filename = f"role_{uuid.uuid4().hex}{os.path.splitext(source)[1].lower()}"
        target = os.path.join(UPLOAD_FOLDER, filename)
        shutil.copyfile(source, target)
        return jsonify({'success': True, 'path': f'uploads/{filename}'})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

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

        # The dashboard only needs addresses and the password-presence flags below.
        config = dict(config)
        config.pop('linkedin', None)
        return jsonify({'success': True, 'config': config})

    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/credentials-status')
def credentials_status():
    credentials = {}
    if os.path.exists('linkedin_credentials.json'):
        try:
            with open('linkedin_credentials.json', encoding='utf-8') as source:
                credentials = json.load(source)
        except (OSError, ValueError):
            credentials = {}
    gmail = credentials.get('gmail') or {}
    return jsonify({
        'linkedinEmail': credentials.get('email', ''),
        'gmailEmail': gmail.get('senderEmail', ''),
        'hasLinkedinPassword': bool(credentials.get('password')),
        'hasGmailPassword': bool(gmail.get('senderPassword')),
    })

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
        print("🚀 LinkedIn AutoBot Professional Dashboard")
        print("=" * 60)
        print(f"Dashboard URL: http://localhost:5000")
        print(f"API Base URL: http://localhost:5000/api")
        print("=" * 60)
        print()
        print("Features:")
        print("✅ Complete user configuration")
        print("✅ Resume upload & management")
        print("✅ Job role templates")
        print("✅ Email and networking automation")
        print("✅ Real-time statistics")
        print("✅ Data export capabilities")
        print("✅ Professional UI design")
        print()
        print("Starting server...")

        app.run(host='127.0.0.1', port=5000, debug=False)

    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        bot_controller.stop_bot()
        print("Server stopped.")
    except Exception as e:
        logging.error(f"Error starting server: {e}")
        print(f"Failed to start server: {e}")
