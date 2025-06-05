# Data Ingestion API System

A Django-based RESTful API system for handling data ingestion requests with priority-based batch processing, rate limiting, and asynchronous processing.

## Features

- **Batch Processing**: Automatically splits large requests into batches of 3 IDs
- **Priority Queue**: Processes requests based on priority (HIGH > MEDIUM > LOW) and creation time
- **Rate Limiting**: Respects 1 batch per 5-second rate limit
- **Asynchronous Processing**: Background processing with real-time status updates
- **Status Tracking**: Comprehensive status tracking for ingestion requests and individual batches
- **Comprehensive Testing**: Extensive test suite covering all requirements

## Requirements

- Python 3.8+
- Django 4.2+
- Django REST Framework

## Setup Instructions

### 1. Clone or Create Project Structure

```bash
mkdir data_ingestion_api
cd data_ingestion_api
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Django Project

```bash
# Create Django project structure
django-admin startproject data_ingestion_api .
python manage.py startapp ingestion

# Run migrations
python manage.py makemigrations
python manage.py migrate
```

### 5. Start Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## 🔌 API Endpoints

### POST /ingest
Submit a data ingestion request.

**Request Body:**
```json
{
    "ids": [1, 2, 3, 4, 5],
    "priority": "HIGH"
}
```

**Response:**
```json
{
    "ingestion_id": "abc123-def456-ghi789"
}
```

**Priority Options:**
- `HIGH`: Highest priority processing
- `MEDIUM`: Medium priority processing  
- `LOW`: Lowest priority processing

### GET /status/<ingestion_id>
Check the status of an ingestion request.

**Response:**
```json
{
    "ingestion_id": "abc123-def456-ghi789",
    "status": "triggered",
    "batches": [
        {
            "batch_id": "batch-uuid-1",
            "ids": [1, 2, 3],
            "status": "completed"
        },
        {
            "batch_id": "batch-uuid-2", 
            "ids": [4, 5],
            "status": "triggered"
        }
    ]
}
```

**Status Values:**
- `yet_to_start`: Processing hasn't begun
- `triggered`: Processing is in progress
- `completed`: Processing is finished

## Testing

### Run Comprehensive Tests

```bash
python test_api.py
```

### Test with Custom URL

```bash
python test_api.py http://your-deployed-url.com
```

### Manual Testing Examples

```bash
# Submit ingestion request
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3, 4, 5], "priority": "HIGH"}'

# Check status
curl http://localhost:8000/status/abc123-def456-ghi789

# Health check
curl http://localhost:8000/health
```

## Architecture & Design Decisions

### Priority Queue Implementation
- Uses Python's `heapq` for efficient priority-based processing
- Priorities: HIGH=1, MEDIUM=2, LOW=3 (lower number = higher priority)
- Secondary sorting by creation time for FIFO within same priority

### Rate Limiting Strategy
- Global rate limiter ensures max 1 batch per 5 seconds
- Thread-safe implementation using locks
- Queued batches wait for their turn based on rate limit

### Asynchronous Processing
- Background worker thread processes batches continuously
- Non-blocking API responses - immediate return of ingestion_id
- Real-time status updates as batches progress

### Data Storage
- Django models for persistent storage
- SQLite database for development (easily switchable to PostgreSQL/MySQL)
- JSON field for storing batch IDs list

### Batch Management
- Automatic splitting of large ID lists into batches of 3
- Each batch tracked independently with unique UUID
- Status aggregation from individual batch statuses

## Test Coverage

The test suite covers:

1. **Basic Functionality**
   - API connectivity and health checks
   - Ingestion request creation
   - Status retrieval

2. **Core Requirements**
   - Batch size limiting (max 3 IDs per batch)
   - Priority-based processing order
   - Rate limiting (1 batch per 5 seconds)
   - Status transitions (yet_to_start → triggered → completed)

3. **Edge Cases**
   - Invalid input handling
   - Concurrent request processing
   - Large batch handling (100+ IDs)
   - Error recovery

4. **Performance**
   - Response time validation
   - Concurrent request handling
   - Rate limit compliance

## Deployment

### Local Development
```bash
python manage.py runserver 0.0.0.0:8000
```

### Production Deployment

#### Using Gunicorn
```bash
pip install gunicorn
gunicorn data_ingestion_api.wsgi:application --bind 0.0.0.0:8000
```

#### Environment Variables
```bash
export DJANGO_SETTINGS_MODULE=data_ingestion_api.settings
export DEBUG=False
export ALLOWED_HOSTS=your-domain.com
```

#### Docker Deployment
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python manage.py migrate
EXPOSE 8000
CMD ["gunicorn", "data_ingestion_api.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Popular Hosting Platforms

#### Railway
1. Connect GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python manage.py migrate && gunicorn data_ingestion_api.wsgi:application --host 0.0.0.0 --port $PORT`

#### Heroku
1. Create `Procfile`: `web: gunicorn data_ingestion_api.wsgi:application`
2. Add `runtime.txt`: `python-3.9.16`
3. Deploy via Git or GitHub integration

#### Render
1. Connect repository
2. Set build command: `pip install -r requirements.txt && python manage.py migrate`
3. Set start command: `gunicorn data_ingestion_api.wsgi:application`

## 🔧 Configuration

### Settings Customization

Key settings in `settings.py`:

```python
# Database (switch to PostgreSQL for production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Security (for production)
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']
SECRET_KEY = 'your-secret-key'
```

### Rate Limiting Configuration

In `tasks.py`, modify the `BatchProcessor` class:

```python
self.rate_limit_seconds = 5  # Change rate limit
batch_size = 3              # Change batch size
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   python manage.py runserver 8001
   ```

2. **Database migration errors**
   ```bash
   python manage.py makemigrations --empty ingestion
   python manage.py migrate
   ```

3. **Rate limiting not working**
   - Check if background worker thread is running
   - Verify no exceptions in processing

4. **Tests failing**
   - Ensure API server is running on correct port
   - Check network connectivity
   - Verify all dependencies installed

## API Response Examples

### Successful Ingestion
```json
{
    "ingestion_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Status Response
```json
{
    "ingestion_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "triggered",
    "batches": [
        {
            "batch_id": "batch-uuid-1",
            "ids": [1, 2, 3],
            "status": "completed"
        },
        {
            "batch_id": "batch-uuid-2",
            "ids": [4, 5],
            "status": "triggered"
        }
    ]
}
```

### Error Response
```json
{
    "error": "Invalid input",
    "details": {
        "ids": ["This field is required."],
        "priority": ["This field is required."]
    }
}
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request
#   L o o p A I p r o j  
 