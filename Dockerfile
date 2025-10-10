# Lightweight Dockerfile for SageMaker (without nginx)
# Use this if you don't need nginx reverse proxy

FROM python:3.11-slim

LABEL maintainer="AI Service Team"
LABEL description="AWS SageMaker compatible AI service container - Lightweight"

# Set environment variables for SageMaker
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/ml/code:${PATH}" \
    SAGEMAKER_PROGRAM=serve \
    SAGEMAKER_SUBMIT_DIRECTORY=/opt/ml/code \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create SageMaker directory structure
RUN mkdir -p /opt/ml/code \
    /opt/ml/input \
    /opt/ml/model \
    /opt/ml/output

# Set working directory
WORKDIR /opt/ml/code

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /opt/ml/code/app/
COPY serve /opt/ml/code/serve
COPY train /opt/ml/code/train

# Make scripts executable
RUN chmod +x /opt/ml/code/serve /opt/ml/code/train

# Create non-root user for security
RUN useradd -m -u 1000 sagemaker && \
    chown -R sagemaker:sagemaker /opt/ml

# Switch to non-root user
USER sagemaker

# Expose SageMaker port
EXPOSE 8080

# Health check using curl
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ping || exit 1

# Default command runs the serve script
ENTRYPOINT ["python"]
CMD ["/opt/ml/code/serve"]
