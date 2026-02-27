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

# Use Tsinghua mirror for pip wheel - critical for stability
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple


# Stage 2: Final
FROM continuumio/miniconda3:latest

WORKDIR /app

# Configure conda with Tsinghua mirrors (faster and more stable in China)
# Skip conda update to avoid network issues, use pre-installed version
RUN conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main && \
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free && \
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge && \
    conda config --set show_channel_urls yes && \
    # Try to install libmamba solver (faster), but don't fail if it doesn't work
    conda install -y conda-forge::conda-libmamba-solver -c conda-forge || true && \
    conda config --set solver libmamba || true && \
    conda clean -afy

# Install runtime dependencies & Browser environment in ONE command (reduce layers)
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
# Use Tsinghua mirror for pip installs
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# Pre-install Playwright and its browsers (Chromium only to save space)
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
