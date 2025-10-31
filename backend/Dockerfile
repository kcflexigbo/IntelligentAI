# --- Stage 1: Build the application with pip ---
FROM pytorch/pytorch:2.9.0-cuda13.0-cudnn9-runtime as builder

# Set working directory
WORKDIR /app

# Copy only the dependency file to leverage Docker layer caching
COPY ./pyproject.toml ./

# Install dependencies using pip into the global site-packages
# It is recommended to first inspect the base image for pre-installed packages
# and only install the ones that are missing.
# For example: RUN pip install --no-cache-dir -r requirements.txt
# where requirements.txt is generated from pyproject.toml and excludes existing packages.
# For simplicity, this example installs all dependencies from pyproject.toml.
RUN pip install --no-cache-dir .

RUN pip install --no-cache-dir pgvector asyncpg langchain_huggingface

# --- Stage 2: Create the final production image ---
FROM pytorch/pytorch:2.9.0-cuda13.0-cudnn9-runtime

WORKDIR /app

# Copy the conda environment (which includes Python and installed packages)
# PyTorch images are conda-based; copying /opt/conda preserves installed deps.
COPY --from=builder /opt/conda /opt/conda

# Ensure conda/python are available in PATH
ENV PATH="/opt/conda/bin:${PATH}"

# Copy the application source code
COPY ./backend/app /app/app
COPY ./alembic /app/app/alembic
COPY ./alembic.ini /app/app/alembic.ini

# Expose the port the app runs on
EXPOSE 8000

# Run alembic migrations and then start the server
# This command ensures migrations are applied every time the container starts.
CMD ["sh", "-c", "pwd && ls app  && alembic --config app/alembic.ini upgrade head && uvicorn app.main:app --workers 5 --host 0.0.0.0 --port 8000"]