# --- Stage 1: Build the application with uv ---
FROM python:3.13-slim as builder

# Set working directory
WORKDIR /app

# Install uv using pip
RUN pip install --no-cache-dir uv

# Copy only the dependency files to leverage Docker layer caching
COPY ./pyproject.toml ./uv.lock* ./

# Install dependencies without dev dependencies
# Increase timeout for large packages like torch (846MB+)
ENV UV_HTTP_TIMEOUT=300
# Use cache mount to persist uv cache between builds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Stage 2: Create the final production image ---
FROM python:3.13-slim

WORKDIR /app

# Install uv in the final image
RUN pip install --no-cache-dir uv

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the application source code
COPY ./backend/app /app/app
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

# Ensure we use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Run alembic migrations and then start the server
# This command ensures migrations are applied every time the container starts.
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]