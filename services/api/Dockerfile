# Dockerfile for API service
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements (if we had a separate requirements file for services)
# For now, we'll install dependencies directly
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    requests \
    kubernetes \
    psycopg2-binary

# Copy application code
COPY services/ /app/services/
COPY tools/ /app/tools/
COPY models.py /app/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run API service
CMD ["python", "-m", "services.api.api"]
