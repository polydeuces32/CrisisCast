#!/usr/bin/env python3
"""
CrisisCast - Main startup script
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

if __name__ == "__main__":
 print(" Starting CrisisCast API...")
 print("=" * 50)
 print("API Documentation: http://localhost:8000/docs")
 print("Health Check: http://localhost:8000/health")
 print("=" * 50)

 uvicorn.run(
 "app.main:app",
 host="127.0.0.1",
 port=8000,
 reload=True
 )

