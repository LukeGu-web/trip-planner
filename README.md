# Trip Planner

A journey planning service based on the Transport for NSW API, supporting real-time trip queries, fare calculations, and journey optimization.

## Features

- Real-time journey planning and queries
- Opal card fare calculation (based on latest distance tables)
- Peak/Off-peak fare differentiation
- Multi-modal transport support (Train, Bus, etc.)
- Real-time arrival and delay information

## Requirements

- Python 3.12+
- Redis server (for caching)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/trip-planner.git
cd trip-planner
```

2. Create and activate virtual environment:
```bash
# Create virtual environment
python3 -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Dependencies

```plaintext
# HTTP client
httpx==0.27.0  # For API requests

# FastAPI framework and dependencies
fastapi==0.110.0  # Web framework
uvicorn==0.27.1  # ASGI server
pydantic==2.6.3  # Data validation
pydantic-settings==2.2.1  # Configuration management

# Data processing
pandas==2.2.1  # Data analysis
openpyxl==3.1.2  # Excel file support

# Date and time handling
pytz==2024.1  # Timezone support

# Redis support
aioredis==2.0.1  # Async Redis client

# Testing
pytest==8.0.2  # Testing framework
pytest-asyncio==0.23.5  # Async testing support

# Development tools
python-dotenv==1.0.1  # Environment variable management
```

## Configuration

1. Create a `.env` file and set the necessary environment variables:
```env
TFNSW_API_KEY=your_api_key
TFNSW_API_BASE_URL=https://api.transport.nsw.gov.au
REDIS_HOST=localhost
REDIS_PORT=6379
```

2. Ensure Redis server is running (if using)

## Running the Service

```bash
# Development mode
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

After starting the service, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development Guide

- Update dependencies list: `pip freeze > requirements.txt`
- Run tests: `pytest`
- Format code: `black .`

## Important Notes

- Ensure you have a valid Transport for NSW API key
- Keep the distance table file (`open-data-opal-distance-tables-2024-12.xlsx`) up to date
- Be aware that peak hour definitions may change

## License

[MIT License](LICENSE)
