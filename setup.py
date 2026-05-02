#!/usr/bin/env python3
"""
CrisisCast Setup Script
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def run_command(command, description):
 """Run a command and handle errors"""
 print(f" {description}...")
 try:
 result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
 print(f"[OK] {description} completed")
 return True
 except subprocess.CalledProcessError as e:
 print(f"[ERROR] {description} failed: {e}")
 print(f"Error output: {e.stderr}")
 return False

def check_python_version():
 """Check if Python version is compatible"""
 if sys.version_info < (3, 8):
 print("[ERROR] Python 3.8 or higher is required")
 sys.exit(1)
 print(f"[OK] Python {sys.version.split()[0]} detected")

def check_redis():
 """Check if Redis is available"""
 try:
 import redis
 r = redis.Redis(host='localhost', port=6379, db=0)
 r.ping()
 print("[OK] Redis is running")
 return True
 except Exception as e:
 print(f"[ERROR] Redis is not available: {e}")
 print("Please install and start Redis:")
 print(" macOS: brew install redis && brew services start redis")
 print(" Ubuntu: sudo apt install redis-server && sudo systemctl start redis")
 return False

def install_dependencies():
 """Install Python dependencies"""
 return run_command("pip install -r requirements.txt", "Installing Python dependencies")

def create_directories():
 """Create necessary directories"""
 directories = [
 "data/raw",
 "data/processed", 
 "data/models",
 "logs"
 ]
 
 for directory in directories:
 os.makedirs(directory, exist_ok=True)
 print(f"[OK] Created directory: {directory}")

def setup_environment():
 """Set up environment file"""
 env_file = Path(".env")
 env_example = Path("config.env.example")
 
 if not env_file.exists() and env_example.exists():
 import shutil
 shutil.copy(env_example, env_file)
 print("[OK] Created .env file from template")
 print("[WARNING] Please edit .env file with your API keys and configuration")
 elif env_file.exists():
 print("[OK] .env file already exists")
 else:
 print("[WARNING] No .env file found, please create one manually")

async def initialize_database():
 """Initialize the database"""
 try:
 sys.path.append(str(Path(__file__).parent))
 from app.core.database import init_db
 
 print(" Initializing database...")
 await init_db()
 print("[OK] Database initialized")
 return True
 except Exception as e:
 print(f"[ERROR] Database initialization failed: {e}")
 return False

def make_executable():
 """Make scripts executable"""
 scripts = [
 "run.py",
 "scripts/crisiscast_cli.py"
 ]
 
 for script in scripts:
 if os.path.exists(script):
 os.chmod(script, 0o755)
 print(f"[OK] Made {script} executable")

def run_tests():
 """Run basic tests"""
 print(" Running basic tests...")
 
 # Test imports
 try:
 sys.path.append(str(Path(__file__).parent))
 from app.main import app
 from app.core.config import settings
 from app.services.ml_service import MLService
 from app.services.data_ingestion import DataIngestionService
 from app.services.alert_service import AlertService
 print("[OK] All imports successful")
 except Exception as e:
 print(f"[ERROR] Import test failed: {e}")
 return False
 
 # Test configuration
 try:
 print(f"[OK] Configuration loaded: {len(settings.supported_markets)} markets supported")
 except Exception as e:
 print(f"[ERROR] Configuration test failed: {e}")
 return False
 
 return True

def main():
 """Main setup function"""
 print(" CrisisCast Setup")
 print("=" * 50)
 
 # Check Python version
 check_python_version()
 
 # Check Redis
 if not check_redis():
 print("\n[WARNING] Redis is required for CrisisCast to function properly")
 print("Please install and start Redis, then run this setup again")
 return
 
 # Install dependencies
 if not install_dependencies():
 print("[ERROR] Setup failed during dependency installation")
 return
 
 # Create directories
 create_directories()
 
 # Setup environment
 setup_environment()
 
 # Make scripts executable
 make_executable()
 
 # Initialize database
 if not asyncio.run(initialize_database()):
 print("[ERROR] Setup failed during database initialization")
 return
 
 # Run tests
 if not run_tests():
 print("[ERROR] Setup failed during testing")
 return
 
 print("\n CrisisCast setup completed successfully!")
 print("\nNext steps:")
 print("1. Edit .env file with your API keys")
 print("2. Start the API server: python run.py")
 print("3. Use the CLI: python scripts/crisiscast_cli.py --help")
 print("4. Visit http://localhost:8000/docs for API documentation")

if __name__ == "__main__":
 main()
