# Dockerfile for FastAPI application
FROM python:3.11-slim

# System deps (optional, add if your libs need gcc, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
&& rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy dependency file(s) first
COPY requirements.txt .

# Install deps
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Port Railway will map to $PORT
ENV PORT 8000
EXPOSE $PORT

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
