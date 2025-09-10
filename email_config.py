"""
LinkedIn Email Extractor Configuration
Modify these settings according to your preferences
"""

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "thamimansari358@gmail.com"  # Your Gmail address
SENDER_PASSWORD = "fjld gcow xequ fhgp"     # Your Gmail app password

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
RESUME_FILE = "Thamim_Ansari_Resume.pdf"

# Job Search Limits - Set to high numbers for continuous processing
MAX_JOBS_PER_SEARCH = 500   # Maximum jobs to process (set high for continuous scrolling)
MAX_PAGES = 10              # Maximum pages to scroll through (set high for continuous scrolling)
DELAY_BETWEEN_EMAILS = 3    # Seconds to wait between sending emails (increased for safety)
DELAY_BETWEEN_JOBS = 2      # Seconds to wait between processing jobs (increased for stability)

# Email Template
EMAIL_SUBJECT = "Application for React.js Developer / Frontend Developer – 3+ Years Experience"

EMAIL_BODY = """
<html>
<head>
    <style>
        body { 
            font-family: 'Poppins', Arial, sans-serif; 
            line-height: 1.6; 
            color: #333;
            margin: 0;
            padding: 20px;
        }
        p { margin: 12px 0; }
        ul { margin: 12px 0; padding-left: 25px; }
        li { margin: 6px 0; }
        strong { font-weight: 600; }
        a { color: #0066CC; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
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
