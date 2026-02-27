# Stage 1: Builder
FROM continuumio/miniconda3:latest AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Create wheels
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# Stage 2: Final
FROM continuumio/miniconda3:latest

WORKDIR /app

# Install runtime dependencies & Browser environment
# 1. Basic Tools: git, curl, tzdata
# 2. Selenium/DrissionPage: chromium, chromium-driver
# 3. Fonts: fonts-noto-cjk (Chinese)
# 4. Playwright Dependencies: libnss3, libnspr4, libgbm1, libasound2, etc. (Commonly needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    tzdata \
    p7zip-full \
    unrar-free \
    chromium \
    chromium-driver \
    fonts-noto-cjk \
    libnss3 \
    libnspr4 \
    libgbm1 \
    libasound2 \
    libxss1 \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome environment variables for Selenium/DrissionPage
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Pre-install Playwright and its browsers (Chromium only to save space, user can install others if needed)
# This ensures system dependencies are fully ready and the browser binary is cached
RUN pip install --no-cache-dir playwright \
    && playwright install chromium \
    && playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .

# Install dependencies from wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels \
    && conda clean -afy

# Pre-create envs directory to avoid permission issues
RUN mkdir -p /app/envs /app/logs/tasks /app/logs/install /app/data/backups

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
