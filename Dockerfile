FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    rsync \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .

# Install system Python dependencies for the main application
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Create virtual environment for XMP tool
RUN python -m venv .venv

# Install requirements into the virtual environment
RUN .venv/bin/pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application files
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY resources/ ./resources/
COPY config.yaml ./ 

# Make scripts executable
RUN chmod +x scripts/*.sh scripts/entrypoint.sh

# Create directory for SSH keys (will be mounted as volume)
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Create directory for local sync destination (will be mounted as volume)
RUN mkdir -p /media

# Create log directory structure (will be mounted as volume)
RUN mkdir -p /app/logs/vastai/api \
    && mkdir -p /app/logs/vastai/instances \
    && mkdir -p /app/logs/sync/operations \
    && mkdir -p /app/logs/sync/progress \
    && mkdir -p /app/logs/app

# Create downloads directory for queue and status files
RUN mkdir -p /app/downloads

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.sync.sync_api

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/status || exit 1

# Run the application using entrypoint script
CMD ["./scripts/entrypoint.sh"]