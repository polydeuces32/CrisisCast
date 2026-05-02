#!/bin/bash

echo " Starting CrisisCast..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
 echo "[ERROR] Python 3 is not installed. Please install Python 3.8+ and try again."
 exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
 echo "[ERROR] Python $PYTHON_VERSION detected. Please install Python 3.8+ and try again."
 exit 1
fi

echo "[OK] Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
 echo " Creating virtual environment..."
 python3 -m venv .venv
fi

# Activate virtual environment
echo " Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo " Installing dependencies..."
pip install -r requirements.txt

# Check if port 8000 is in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
 echo "[WARNING] Port 8000 is already in use. Trying to kill the process..."
 lsof -ti:8000 | xargs kill -9 2>/dev/null || true
 sleep 2
fi

# Set environment variables for development
export DATABASE_URL="sqlite:///./crisiscast.db"
export REDIS_URL="redis://localhost:6379/0"

# Start the application
echo " Starting CrisisCast API..."
echo "=================================================="
echo "API Documentation: http://localhost:8000/docs"
echo "Health Check: http://localhost:8000/health"
echo "=================================================="
echo "Press Ctrl+C to stop the server"
echo ""

python run.py
