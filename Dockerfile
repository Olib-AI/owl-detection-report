FROM python:3.12-slim

# System deps for Playwright + Puppeteer Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS for Puppeteer
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies + Playwright Chromium
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

# Puppeteer-core (uses Playwright's Chromium — no extra download)
RUN npm init -y > /dev/null 2>&1 \
    && npm install puppeteer-core

COPY src/ src/

ENV OUTPUT_DIR=/output
VOLUME ["/output"]

ENTRYPOINT ["python", "-m", "src.main"]
