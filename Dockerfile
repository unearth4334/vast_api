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
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application files
COPY *.py ./
COPY *.sh ./
COPY config.yaml ./ 

# Make scripts executable
RUN chmod +x *.sh

# Create directory for SSH keys (will be mounted as volume)
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Create directory for local sync destination (will be mounted as volume)
RUN mkdir -p /media

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=sync_api.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/status || exit 1

# Run the application
CMD ["python", "sync_api.py"]