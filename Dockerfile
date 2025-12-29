# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for frontend building
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Copy Python requirements and install dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Build the frontend
WORKDIR /app/src/lesson_generator/web/frontend
RUN npm install && npm run build

# Go back to app directory
WORKDIR /app

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Create directories for generated lessons and logs
RUN mkdir -p /app/generated_lessons /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/api/v1/system/health || exit 1

# Expose port
EXPOSE $PORT

# Run the application
CMD ["python", "-m", "lesson_generator.web.main", "--host", "0.0.0.0", "--port", "8000"]