#!/usr/bin/env python3
"""
LinkedIn AutoBot Dashboard API Server
Provides REST API endpoints to control email extractor and RunAiBot
"""

import os
import sys
import json
import time
import threading
import subprocess
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import logging
import pandas as pd
import csv
from io import BytesIO

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

class BotController:
    def __init__(self):
        self.email_extractor_process = None
        self.aibot_process = None
        self.stats = {
            'email_extractor': {
                'emails_extracted': 0,
                'emails_sent': 0,
                'posts_processed': 0,
                'status': 'stopped'
            },
            'aibot': {
                'jobs_applied': 0,
                'jobs_external': 0,
                'jobs_failed': 0,
                'status': 'stopped'
            },
            'recent_emails': [],
            'recent_applications': []
        }
        self.start_time = datetime.now()
        
    def start_email_extractor(self, job_config=None):
        """Start the LinkedIn email extractor"""
        try:
            if self.email_extractor_process and self.email_extractor_process.poll() is None:
                return {'success': False, 'error': 'Email extractor is already running'}
            
            # Write job configuration to a temp file if provided
            if job_config:
                with open('temp_job_config.json', 'w') as f:
                    json.dump(job_config, f)
                logging.info(f"Job config saved: {job_config}")
            
            # Start the email extractor process
            self.email_extractor_process = subprocess.Popen([
                sys.executable, 'linkedin_email_extractor.py'
            ], text=True, cwd=os.getcwd())
            
            self.stats['email_extractor']['status'] = 'running'
            
            # Wait a moment to check if process started successfully
            time.sleep(2)
            if self.email_extractor_process.poll() is not None:
                # Process ended immediately, check for errors
                logging.error(f"Email extractor process ended immediately with return code: {self.email_extractor_process.returncode}")
                self.stats['email_extractor']['status'] = 'error'
                return {'success': False, 'error': f'Email extractor failed to start (return code: {self.email_extractor_process.returncode})'}
            
            logging.info("Email extractor process started successfully")
            
            # Start monitoring thread
            threading.Thread(target=self._monitor_email_extractor, daemon=True).start()
            
            return {'success': True, 'message': 'Email extractor started successfully'}
            
        except Exception as e:
            logging.error(f"Error starting email extractor: {e}")
            return {'success': False, 'error': str(e)}
    
    def stop_email_extractor(self):
        """Stop the LinkedIn email extractor"""
        try:
            if self.email_extractor_process:
                self.email_extractor_process.terminate()
                self.email_extractor_process.wait(timeout=10)
                self.email_extractor_process = None
                
            self.stats['email_extractor']['status'] = 'stopped'
            return {'success': True, 'message': 'Email extractor stopped successfully'}
            
        except Exception as e:
            logging.error(f"Error stopping email extractor: {e}")
            return {'success': False, 'error': str(e)}
    
    def start_aibot(self):
        """Start the RunAiBot"""
        try:
            if self.aibot_process and self.aibot_process.poll() is None:
                return {'success': False, 'error': 'RunAiBot is already running'}
            
            # Start the RunAiBot process
            self.aibot_process = subprocess.Popen([
                sys.executable, 'runAiBot.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            self.stats['aibot']['status'] = 'running'
            
            # Start monitoring thread
            threading.Thread(target=self._monitor_aibot, daemon=True).start()
            
            return {'success': True, 'message': 'RunAiBot started successfully'}
            
        except Exception as e:
            logging.error(f"Error starting RunAiBot: {e}")
            return {'success': False, 'error': str(e)}
    
    def stop_aibot(self):
        """Stop the RunAiBot"""
        try:
            if self.aibot_process:
                self.aibot_process.terminate()
                self.aibot_process.wait(timeout=10)
                self.aibot_process = None
                
            self.stats['aibot']['status'] = 'stopped'
            return {'success': True, 'message': 'RunAiBot stopped successfully'}
            
        except Exception as e:
            logging.error(f"Error stopping RunAiBot: {e}")
            return {'success': False, 'error': str(e)}
    
    def _monitor_email_extractor(self):
        """Monitor email extractor process and update stats"""
        while self.email_extractor_process and self.email_extractor_process.poll() is None:
            try:
                # Try to read stats from log files or output
                self._update_email_stats()
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error monitoring email extractor: {e}")
                break
        
        # Process ended
        self.stats['email_extractor']['status'] = 'stopped'
        self.email_extractor_process = None
    
    def _monitor_aibot(self):
        """Monitor RunAiBot process and update stats"""
        while self.aibot_process and self.aibot_process.poll() is None:
            try:
                # Try to read stats from log files or output
                self._update_aibot_stats()
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error monitoring RunAiBot: {e}")
                break
        
        # Process ended
        self.stats['aibot']['status'] = 'stopped'
        self.aibot_process = None
    
    def _update_email_stats(self):
        """Update email extractor statistics"""
        try:
            # First try to read from runtime stats file
            if os.path.exists('dashboard_stats.json'):
                with open('dashboard_stats.json', 'r') as f:
                    runtime_stats = json.load(f)
                    if 'email_extractor' in runtime_stats:
                        email_stats = runtime_stats['email_extractor']
                        self.stats['email_extractor'].update(email_stats)
            
            # Read from sent emails log
            if os.path.exists('sent_emails_log.csv'):
                with open('sent_emails_log.csv', 'r') as f:
                    lines = f.readlines()
                    self.stats['email_extractor']['emails_sent'] = len(lines) - 1  # Subtract header
                    
                    # Update recent emails
                    recent_emails = []
                    for line in lines[-6:]:  # Last 5 emails
                        if line.strip() and ',' in line:
                            parts = line.strip().split(',')
                            if len(parts) >= 2:
                                recent_emails.append({
                                    'email': parts[0],
                                    'status': 'sent',
                                    'time': parts[1] if len(parts) > 1 else 'Unknown'
                                })
                    self.stats['recent_emails'] = recent_emails
            
            # Read from extracted emails log
            if os.path.exists('extracted_emails.json'):
                with open('extracted_emails.json', 'r') as f:
                    data = json.load(f)
                    self.stats['email_extractor']['emails_extracted'] = data.get('total_count', 0)
                    self.stats['email_extractor']['posts_processed'] = data.get('posts_processed', 0)
                    
        except Exception as e:
            logging.error(f"Error updating email stats: {e}")
    
    def _update_aibot_stats(self):
        """Update RunAiBot statistics"""
        try:
            # Read from applied jobs Excel file
            excel_files = [
                'all excels/all_applied_applications_history.xlsx',
                'all_applied_applications_history.xlsx'
            ]
            
            for excel_file in excel_files:
                if os.path.exists(excel_file):
                    try:
                        import pandas as pd
                        df = pd.read_excel(excel_file)
                        
                        # Count different types of applications
                        total_applications = len(df)
                        external_applications = len(df[df['External Job link'].notna() & 
                                                    (df['External Job link'] != 'Easy Applied')])
                        easy_applications = total_applications - external_applications
                        
                        self.stats['aibot']['jobs_applied'] = easy_applications
                        self.stats['aibot']['jobs_external'] = external_applications
                        
                        # Update recent applications
                        recent_apps = []
                        for _, row in df.tail(5).iterrows():
                            recent_apps.append({
                                'company': row.get('Company', 'Unknown'),
                                'position': row.get('Title', 'Unknown'),
                                'status': 'applied' if row.get('External Job link') == 'Easy Applied' else 'external',
                                'time': str(row.get('Date Applied', 'Unknown')),
                                'link': row.get('Job Link', '#')
                            })
                        self.stats['recent_applications'] = recent_apps
                        break
                        
                    except ImportError:
                        logging.warning("pandas not available, cannot read Excel files")
                    except Exception as e:
                        logging.error(f"Error reading Excel file {excel_file}: {e}")
            
            # Read failed jobs
            failed_files = [
                'all excels/all_failed_applications_history.xlsx',
                'all_failed_applications_history.xlsx'
            ]
            
            for failed_file in failed_files:
                if os.path.exists(failed_file):
                    try:
                        import pandas as pd
                        df_failed = pd.read_excel(failed_file)
                        self.stats['aibot']['jobs_failed'] = len(df_failed)
                        break
                    except:
                        pass
                        
        except Exception as e:
            logging.error(f"Error updating aibot stats: {e}")

# Initialize bot controller
bot_controller = BotController()

@app.route('/')
def index():
    """Serve the dashboard"""
    return render_template('index.html')

@app.route('/api/start-email-extractor', methods=['POST'])
def start_email_extractor():
    """Start the email extractor"""
    try:
        # Get job configuration from request
        job_config = None
        if request.json:
            job_config = request.json.get('config')
            job_role = request.json.get('jobRole', 'react')
            logging.info(f"Starting email extractor with job role: {job_role}")
        
        result = bot_controller.start_email_extractor(job_config)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error in start_email_extractor endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop-email-extractor', methods=['POST'])
def stop_email_extractor():
    """Stop the email extractor"""
    result = bot_controller.stop_email_extractor()
    return jsonify(result)

@app.route('/api/start-aibot', methods=['POST'])
def start_aibot():
    """Start the RunAiBot"""
    result = bot_controller.start_aibot()
    return jsonify(result)

@app.route('/api/stop-aibot', methods=['POST'])
def stop_aibot():
    """Stop the RunAiBot"""
    result = bot_controller.stop_aibot()
    return jsonify(result)

@app.route('/api/stats')
def get_stats():
    """Get current statistics"""
    return jsonify(bot_controller.stats)

@app.route('/api/status')
def get_status():
    """Get current status of both bots"""
    email_running = bot_controller.email_extractor_process and bot_controller.email_extractor_process.poll() is None
    aibot_running = bot_controller.aibot_process and bot_controller.aibot_process.poll() is None
    
    return jsonify({
        'email_extractor_running': email_running,
        'aibot_running': aibot_running,
        'uptime': str(datetime.now() - bot_controller.start_time)
    })

@app.route('/api/logs/<bot_type>')
def get_logs(bot_type):
    """Get logs for specific bot"""
    try:
        if bot_type == 'email':
            log_file = 'logs/email_extractor.log'
        elif bot_type == 'aibot':
            log_file = 'logs/log.txt'
        else:
            return jsonify({'error': 'Invalid bot type'}), 400
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = f.readlines()[-100:]  # Last 100 lines
            return jsonify({'logs': logs})
        else:
            return jsonify({'logs': []})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sent-emails')
def get_sent_emails():
    """Get all sent emails with pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        if not os.path.exists('sent_emails_log.csv'):
            return jsonify({
                'emails': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            })
        
        # Read all emails from CSV
        emails = []
        with open('sent_emails_log.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                emails.append({
                    'email': row.get('email', ''),
                    'date_sent': row.get('date_sent', ''),
                    'subject': row.get('subject', ''),
                    'status': 'sent'
                })
        
        # Sort by date (newest first)
        emails.sort(key=lambda x: x['date_sent'], reverse=True)
        
        # Calculate pagination
        total = len(emails)
        total_pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        paginated_emails = emails[start_idx:end_idx]
        
        return jsonify({
            'emails': paginated_emails,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-emails-excel')
def download_emails_excel():
    """Download all sent emails as Excel file"""
    try:
        if not os.path.exists('sent_emails_log.csv'):
            return jsonify({'error': 'No sent emails found'}), 404
        
        # Read emails from CSV
        emails_data = []
        with open('sent_emails_log.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                emails_data.append({
                    'Email': row.get('email', ''),
                    'Date Sent': row.get('date_sent', ''),
                    'Subject': row.get('subject', ''),
                    'Status': 'Sent'
                })
        
        # Create DataFrame
        df = pd.DataFrame(emails_data)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sent Emails', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Sent Emails']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Generate filename with current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sent_emails_{timestamp}.xlsx"
        
        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 LinkedIn AutoBot Dashboard API Server")
    print("=" * 60)
    print("Dashboard URL: http://localhost:5000")
    print("API Base URL: http://localhost:5000/api")
    print("=" * 60)
    print("\nStarting server...")
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Start the Flask server
    app.run(host='0.0.0.0', port=5000, debug=True)
