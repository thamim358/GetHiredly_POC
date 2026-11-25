"""
LinkedIn Email Extractor Configuration
Modify these settings according to your preferences
"""

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your.email@gmail.com"              # Your Gmail address (or set it in the dashboard)
SENDER_PASSWORD = "your-16-character-app-password"  # Your Gmail app password (or set it in the dashboard)

# LinkedIn Search Configuration
SEARCH_TERMS = [
    "React Developer",
    "React.js Developer",
    "Frontend Developer",
    "Front End Developer",
    "UI Developer",
    "Web Developer",
    "JavaScript Developer",
    "UI/UX Developer",
    "Frontend Engineer",
    "React Engineer"
]

SEARCH_LOCATION = "India"  # Location for job search

# Date filter for posts - options: "Past 24 hours", "Past week", "Past month", "Any time"
DATE_POSTED = "Past 24 hours"

# Resume file path (relative to script directory)
RESUME_FILE = "uploads/uploaded_resume.pdf"

# Job Search Limits - Set to high numbers for continuous processing
MAX_JOBS_PER_SEARCH = 500   # Maximum jobs to process (set high for continuous scrolling)
MAX_PAGES = 10              # Maximum pages to scroll through (set high for continuous scrolling)
DELAY_BETWEEN_EMAILS = 3    # Seconds to wait between sending emails (increased for safety)
DELAY_BETWEEN_JOBS = 2      # Seconds to wait between processing jobs (increased for stability)

# Email Template
EMAIL_SUBJECT = "Application for React.js Developer / Frontend Developer – 3+ Years Experience"

EMAIL_BODY = """Dear Hiring Manager,

I am writing to apply for the React.js Developer / Frontend Developer position. I have experience building responsive web applications with React, JavaScript, TypeScript, and CSS.

My relevant skills include:

- React and frontend development
- REST API integration and state management
- Responsive design and accessibility
- Git and modern build tools

I have attached my resume for your review. I would welcome the opportunity to discuss how I can contribute to your team.

Thank you for your time and consideration.

Best regards,
[FULL_NAME]
[EMAIL]
[PHONE]
[WEBSITE]
"""
