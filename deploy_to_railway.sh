#!/bin/bash

# Railway.app Deployment Script for LinkedIn AutoBot
# This script helps prepare your repository for Railway deployment

echo "🚀 Preparing LinkedIn AutoBot for Railway.app deployment..."

# Check if we're in the right directory
if [ ! -f "professional_dashboard_api.py" ]; then
    echo "❌ Error: Please run this script from the LinkedIn AutoBot directory"
    exit 1
fi

echo "✅ Found LinkedIn AutoBot files"

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore file..."
    cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
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
EOF
    echo "✅ Created .gitignore"
else
    echo "✅ .gitignore already exists"
fi

# Replace requirements.txt with production version
echo "📦 Updating requirements.txt for production..."
if [ -f "requirements_railway.txt" ]; then
    cp requirements_railway.txt requirements.txt
    echo "✅ Updated requirements.txt with production dependencies"
else
    echo "⚠️  Warning: requirements_railway.txt not found"
fi

# Check Git status
echo "🔍 Checking Git status..."
git status

echo ""
echo "🎯 Next steps:"
echo "1. Review the changes above"
echo "2. Commit your changes:"
echo "   git add ."
echo "   git commit -m 'Add Railway.app deployment configuration'"
echo "   git push origin main"
echo ""
echo "3. Go to railway.app and deploy from your GitHub repository"
echo "4. Follow the detailed guide in RAILWAY_DEPLOYMENT_GUIDE.md"
echo ""
echo "✨ Your LinkedIn AutoBot will be live on Railway.app!"