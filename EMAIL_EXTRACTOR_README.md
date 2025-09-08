# LinkedIn Email Extractor & Auto Sender

This tool automatically searches for jobs on LinkedIn, extracts email addresses from job posts, and sends personalized job applications via email.

## Features

- 🔍 **Smart Job Search**: Searches for React/Frontend developer positions using customizable keywords
- 📧 **Email Extraction**: Automatically extracts email addresses from job descriptions and company pages  
- ✉️ **Auto Email Sending**: Sends personalized job applications with your resume attached
- 📊 **Progress Tracking**: Tracks sent emails to avoid duplicates and provides detailed statistics
- ⚙️ **Configurable**: Easy-to-modify configuration file for all settings

## Setup Instructions

### 1. Prerequisites
- Google Chrome browser installed
- Python 3.7+ installed
- Valid Gmail account with App Password enabled

### 2. Enable Gmail App Password
1. Go to your [Google Account settings](https://myaccount.google.com/)
2. Navigate to Security → 2-Step Verification → App passwords
3. Generate a new app password for "Mail"
4. Copy the 16-character password (this is your `SENDER_PASSWORD`)

### 3. Prepare Your Resume
- Place your resume file in the same directory as the script
- Name it `Thamim_Ansari_Resume.pdf` (or update the filename in `email_config.py`)

### 4. Configure the Tool
Edit `email_config.py` with your details:
```python
# Update these with your information
SENDER_EMAIL = "your-email@gmail.com"
SENDER_PASSWORD = "your-16-char-app-password"
SEARCH_LOCATION = "Your City, Country"
RESUME_FILE = "Your_Resume.pdf"
```

### 5. Install Dependencies
```bash
pip install selenium
```

### 6. Setup ChromeDriver
- Download ChromeDriver from https://chromedriver.chromium.org/
- Place it in your PATH or in the same directory as the script

## Usage

### Option 1: Run the standalone script
```bash
python linkedin_email_extractor.py
```

### Option 2: Use the batch file (Windows)
```bash
run_email_extractor.bat
```

### Option 3: Import into existing project
```python
from linkedin_email_extractor import LinkedInEmailExtractor

extractor = LinkedInEmailExtractor()
extractor.run()
```

## Configuration Options

### Email Settings
- `SENDER_EMAIL`: Your Gmail address
- `SENDER_PASSWORD`: Your Gmail app password
- `EMAIL_SUBJECT`: Subject line for your emails
- `EMAIL_BODY`: HTML email template

### Search Settings
- `SEARCH_TERMS`: List of job titles to search for
- `SEARCH_LOCATION`: Geographic location for job search
- `MAX_JOBS_PER_SEARCH`: Maximum jobs to process per search term
- `DELAY_BETWEEN_EMAILS`: Seconds to wait between sending emails

### Resume
- `RESUME_FILE`: Path to your resume PDF file

## Output Files

The tool creates several files to track progress:

1. **`sent_emails_log.csv`**: Log of all sent emails with timestamps
2. **`extracted_emails.json`**: All extracted email addresses
3. **`linkedin_email_extractor.log`**: Detailed activity log

## Email Template

The default email template includes:
- Professional greeting
- Skills and experience highlights
- Resume attachment
- Contact information

You can customize the template in `email_config.py`.

## Safety Features

- **Duplicate Prevention**: Tracks sent emails to avoid sending duplicates
- **Rate Limiting**: Configurable delays between emails to avoid spam detection  
- **Resume Validation**: Checks if resume file exists before sending
- **Error Handling**: Comprehensive error handling and logging

## Troubleshooting

### Common Issues

1. **"Selenium not found"**
   ```bash
   pip install selenium
   ```

2. **"ChromeDriver not found"**
   - Download ChromeDriver and add to PATH
   - Or place chromedriver.exe in script directory

3. **"Login failed"**
   - Update LinkedIn credentials in config files
   - Check if account requires 2FA

4. **"Email sending failed"**
   - Verify Gmail app password is correct
   - Check SMTP settings

### Tips for Better Results

1. **Use specific job titles** in `SEARCH_TERMS` for better targeting
2. **Set reasonable delays** to avoid being flagged as spam
3. **Monitor logs** for any issues or blocked emails
4. **Update your email template** to match your experience
5. **Test with a few emails first** before running large batches

## Legal & Ethical Considerations

- Use responsibly and in compliance with LinkedIn's Terms of Service
- Respect email recipients and company policies
- Don't send excessive emails to the same companies
- Ensure your emails are professional and relevant

## Support

For issues or questions:
- Check the log files for detailed error information
- Ensure all prerequisites are properly installed
- Verify your configuration settings

## Author

**Thamim Ansari**
- LinkedIn: https://www.linkedin.com/in/thamim358/
- Email: thamimansari358@gmail.com

---

**Good luck with your job search! 🚀**
