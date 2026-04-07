FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# HuggingFace Spaces runs as non-root user, needs write access for model download
RUN chmod -R 777 /app/backend/price_model 2>/dev/null || true

# HF_TOKEN is injected as a Space secret — do not hardcode here
ENV PYTHONUNBUFFERED=1

# HuggingFace Spaces exposes port 7860
EXPOSE 7860

# Run the Dash app via gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "120", "--workers", "1", "--threads", "4", "frontend.app:server"]
