# FastAPI + Redis Project

A sample project built with FastAPI and Redis.

## Requirements

- Python 3.8+
- Redis server
- Project dependencies (see requirements.txt)

## Installation

1. Clone the project:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
Copy `.env.example` to `.env` and modify the configurations as needed.

## Running the Project

1. Ensure Redis server is running

2. Start the application:
```bash
uvicorn app.main:app --reload
```

3. Access API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

- `GET /`: Welcome page
- `GET /ping`: Test Redis connection status

## Testing

Run tests:
```bash
pytest
```
