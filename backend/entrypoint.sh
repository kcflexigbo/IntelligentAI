#!/bin/bash
set -e

echo "=== Starting application startup process ==="

# Navigate to app directory
cd /app

# Wait for database to be ready (simple check)
echo "Waiting for database to be ready..."
python << EOF
import sys
import time
import asyncio
sys.path.insert(0, '/app')

from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

async def check_db():
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect():
            pass
        await engine.dispose()
        return True
    except Exception as e:
        print(f"Database check failed: {e}")
        return False

max_attempts = 30
for attempt in range(max_attempts):
    if asyncio.run(check_db()):
        print("Database is ready!")
        sys.exit(0)
    print(f"Database unavailable - sleeping (attempt {attempt + 1}/{max_attempts})")
    time.sleep(2)

print("Warning: Database connection timeout, continuing anyway...")
sys.exit(0)
EOF

# Run database migrations
echo "=== Running database migrations ==="
alembic --config alembic.ini upgrade head || {
    echo "Warning: Migration failed, continuing anyway..."
}

# Seed course materials (script handles idempotency - checks if materials already exist)
echo "=== Seeding course materials ==="
python << EOF
import sys
sys.path.insert(0, '/app')
import asyncio
from scripts.seed_course_materials import main

try:
    asyncio.run(main())
except Exception as e:
    print(f'Warning: Course seeding encountered an error: {e}')
    import traceback
    traceback.print_exc()
    print('Continuing with application startup...')
EOF

# Start the application with gunicorn and uvicorn workers
echo "=== Starting gunicorn server with uvicorn workers ==="
exec gunicorn app.main:app \
    --workers 5 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50

