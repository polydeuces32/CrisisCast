# 🚀 CrisisCast Setup Guide

## Quick Start (5 minutes)

### Prerequisites
- Python 3.8+ installed
- Git installed
- Internet connection

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/crisiscast.git
cd crisiscast
```

### Step 2: Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Application
```bash
python run.py
```

### Step 5: Access the Application
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Alternative: Docker Setup (Recommended)

### Using Docker Compose
```bash
# Clone the repository
git clone https://github.com/yourusername/crisiscast.git
cd crisiscast

# Run with Docker Compose
docker-compose up -d
```

### Using Docker
```bash
# Build the image
docker build -t crisiscast .

# Run the container
docker run -p 8000:8000 crisiscast
```

## Troubleshooting

### Port 8000 Already in Use
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process
kill <PID>

# Or use a different port
uvicorn app.main:app --port 8001
```

### Database Connection Issues
The application will work without PostgreSQL. It will use SQLite for development.

### Python Version Issues
Make sure you're using Python 3.8 or higher:
```bash
python --version
```

## Features Available

### API Endpoints
- **Forecasts**: `/api/v1/forecasts`
- **Volatility**: `/api/v1/volatility`
- **Alerts**: `/api/v1/alerts`
- **Markets**: `/api/v1/markets`

### CLI Tool
```bash
python scripts/crisiscast_cli.py --help
python scripts/crisiscast_cli.py status
python scripts/crisiscast_cli.py forecast crypto BTC
```

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Open an issue on GitHub
3. Contact us at support@crisiscast.com

## License

MIT License - see LICENSE file for details
