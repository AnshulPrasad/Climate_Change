# create non-root user, create /app, make it owned by user, then run as that user
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# install pip and build deps (run as root)
RUN apt-get update && apt-get install -y \
    python3-pip \
    git \
    curl \
    unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Create app directory and give ownership to appuser
RUN mkdir -p /app && chown -R appuser:appuser /app

# Switch to non-root user and set HOME to /app
USER appuser
ENV HOME=/app
WORKDIR /app

# Copy files as the non-root user (ownership preserved)
COPY --chown=appuser:appuser . /app

# Install Python deps as the non-root user
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
