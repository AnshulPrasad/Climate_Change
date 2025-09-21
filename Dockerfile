# Use official slim Python image
FROM python:3.10-slim

# Avoid interactive prompts, ensure unbuffered stdout
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Install system packages and pip (as root)
RUN apt-get update && apt-get install -y \
    python3-pip \
    build-essential \
    git \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set working dir (create later ownership properly)
WORKDIR /app

# Copy only requirements first so Docker layer caching is efficient
COPY requirements.txt /tmp/requirements.txt

# Upgrade pip and install Python deps system-wide (puts streamlit into /usr/local/bin)
RUN python3 -m pip install --upgrade pip setuptools wheel \
 && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
 # sanity-check: print streamlit path/version if installed (non-fatal)
 && python3 -c "import shutil,sys; p=shutil.which('streamlit'); print('STREAMLIT_BIN=',p); \
    import streamlit as st; print('STREAMLIT_VER=', getattr(st,'__version__','unknown'))" || true

# Create appuser and make /app writable by that user
RUN useradd -m -u 1000 appuser \
 && mkdir -p /app \
 && chown -R appuser:appuser /app

# Copy application code owned by appuser
COPY --chown=appuser:appuser . /app

# Switch to non-root user for runtime
USER appuser
ENV HOME=/home/appuser
WORKDIR /app

# Expose streamlit default port
EXPOSE 7860

# Start Streamlit (runs as appuser)
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
