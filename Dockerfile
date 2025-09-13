FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data/models

# Expose port
EXPOSE 8000

# Set environment variables
ENV DATABASE_URL=sqlite:///./crisiscast.db
ENV REDIS_URL=redis://redis:6379/0

# Run the application
CMD ["python", "run.py"]
