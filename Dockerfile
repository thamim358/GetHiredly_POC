# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome using the new method
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver using webdriver-manager (more reliable)
RUN pip install webdriver-manager

# Copy requirements and install Python dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p "all excels" logs uploads config

# Set environment variables
ENV DISPLAY=:99
ENV ENVIRONMENT=production
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start command with virtual display
# Create a startup script to handle Xvfb and app
RUN echo '#!/bin/bash\n\
# Clean up any existing X server locks\n\
rm -f /tmp/.X*-lock\n\
# Find available display number\n\
DISPLAY_NUM=99\n\
while [ -f "/tmp/.X${DISPLAY_NUM}-lock" ]; do\n\
    DISPLAY_NUM=$((DISPLAY_NUM + 1))\n\
done\n\
export DISPLAY=:${DISPLAY_NUM}\n\
echo "🖥️ Starting Xvfb on display :${DISPLAY_NUM} for non-headless Chrome"\n\
# Start Xvfb with larger screen for LinkedIn\n\
Xvfb :${DISPLAY_NUM} -screen 0 1920x1080x24 -ac +extension GLX +render -noreset -dpi 96 &\n\
sleep 3\n\
echo "✅ Virtual display ready for LinkedIn automation"\n\
# Start the Python application\n\
exec python professional_dashboard_api.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Start the application with proper X server handling
CMD ["/app/start.sh"]