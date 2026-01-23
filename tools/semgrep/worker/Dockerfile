# Multi-stage build for Semgrep worker container
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Semgrep
RUN pip install --no-cache-dir semgrep

# Final stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    boto3 \
    requests

# Copy Semgrep from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/semgrep /usr/local/bin/semgrep

# Set working directory
WORKDIR /app

# Copy worker script
COPY tools/semgrep/worker/worker.py /app/worker.py

# Make worker executable
RUN chmod +x /app/worker.py

# Set entrypoint
ENTRYPOINT ["python", "/app/worker.py"]
