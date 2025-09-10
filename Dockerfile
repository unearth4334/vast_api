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
COPY obsidian_ui/ ./obsidian_ui/
COPY *.sh ./
COPY config.yaml ./ 

# Make scripts executable
RUN chmod +x *.sh

# Create directory for SSH keys (will be mounted as volume)
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Create a script to fix SSH permissions at runtime
RUN echo '#!/bin/bash\n\
# Fix SSH directory and file permissions if needed\n\
if [ -d "/root/.ssh" ]; then\n\
    chmod 700 /root/.ssh 2>/dev/null || true\n\
    [ -f "/root/.ssh/id_ed25519" ] && chmod 600 /root/.ssh/id_ed25519 2>/dev/null || true\n\
    [ -f "/root/.ssh/id_ed25519.pub" ] && chmod 644 /root/.ssh/id_ed25519.pub 2>/dev/null || true\n\
    [ -f "/root/.ssh/config" ] && chmod 644 /root/.ssh/config 2>/dev/null || true\n\
    [ -f "/root/.ssh/known_hosts" ] && chmod 644 /root/.ssh/known_hosts 2>/dev/null || true\n\
    [ -f "/root/.ssh/vast_known_hosts" ] && chmod 664 /root/.ssh/vast_known_hosts 2>/dev/null || true\n\
fi\n\
exec "$@"' > /usr/local/bin/fix-ssh-permissions.sh && \
    chmod +x /usr/local/bin/fix-ssh-permissions.sh

# Create directory for local sync destination (will be mounted as volume)
RUN mkdir -p /media

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.sync.sync_api

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/status || exit 1

# Run the application with permission fix
ENTRYPOINT ["/usr/local/bin/fix-ssh-permissions.sh"]
CMD ["python", "-m", "app.sync.sync_api"]