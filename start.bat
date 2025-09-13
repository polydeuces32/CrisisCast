@echo off
echo 🚀 Starting CrisisCast...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

echo ✅ Python detected

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo 📦 Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Set environment variables for development
set DATABASE_URL=sqlite:///./crisiscast.db
set REDIS_URL=redis://localhost:6379/0

REM Start the application
echo 🚀 Starting CrisisCast API...
echo ==================================================
echo API Documentation: http://localhost:8000/docs
echo Health Check: http://localhost:8000/health
echo ==================================================
echo Press Ctrl+C to stop the server
echo.

python run.py
