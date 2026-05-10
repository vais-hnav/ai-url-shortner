# Use Python 3.10 slim image for smaller size
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata and package source
COPY pyproject.toml .
COPY app ./app

# Install Python dependencies from pyproject.toml
RUN pip install --no-cache-dir .

# Copy runtime files needed by the app
COPY alembic ./alembic
COPY alembic.ini .
COPY docker-compose.yml .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
