# Railway.app Deployment Script for LinkedIn AutoBot (PowerShell)
# This script helps prepare your repository for Railway deployment

Write-Host "🚀 Preparing LinkedIn AutoBot for Railway.app deployment..." -ForegroundColor Green

# Check if we're in the right directory
if (!(Test-Path "professional_dashboard_api.py")) {
    Write-Host "❌ Error: Please run this script from the LinkedIn AutoBot directory" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found LinkedIn AutoBot files" -ForegroundColor Green

# Create .gitignore if it doesn't exist
if (!(Test-Path ".gitignore")) {
    Write-Host "📝 Creating .gitignore file..." -ForegroundColor Yellow
    
    $gitignoreContent = @"
# Python
__pycache__/
*.py[cod]
*`$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# Local development
.env
.vscode/
*.log

# OS
.DS_Store
Thumbs.db

# Application specific
uploads/
logs/
*.xlsx
*.csv
linkedin_credentials.json
bot_stats.json
temp_job_config.json
last_job_config.json

# Chrome
chromedriver.exe
chromedriver
"@

    $gitignoreContent | Out-File -FilePath ".gitignore" -Encoding UTF8
    Write-Host "✅ Created .gitignore" -ForegroundColor Green
} else {
    Write-Host "✅ .gitignore already exists" -ForegroundColor Green
}

# Replace requirements.txt with production version
Write-Host "📦 Updating requirements.txt for production..." -ForegroundColor Yellow

if (Test-Path "requirements_railway.txt") {
    Copy-Item "requirements_railway.txt" "requirements.txt" -Force
    Write-Host "✅ Updated requirements.txt with production dependencies" -ForegroundColor Green
} else {
    Write-Host "⚠️  Warning: requirements_railway.txt not found" -ForegroundColor Yellow
}

# Check Git status
Write-Host "🔍 Checking Git status..." -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "🎯 Next steps:" -ForegroundColor Magenta
Write-Host "1. Review the changes above"
Write-Host "2. Commit your changes:"
Write-Host "   git add ."
Write-Host "   git commit -m 'Add Railway.app deployment configuration'"
Write-Host "   git push origin main"
Write-Host ""
Write-Host "3. Go to railway.app and deploy from your GitHub repository"
Write-Host "4. Follow the detailed guide in RAILWAY_DEPLOYMENT_GUIDE.md"
Write-Host ""
Write-Host "✨ Your LinkedIn AutoBot will be live on Railway.app!" -ForegroundColor Green