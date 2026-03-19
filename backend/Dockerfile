FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake model during build to avoid runtime speed drops
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy app code
COPY . .

# Ensure startup.sh is executable
RUN chmod +x startup.sh

EXPOSE 8000

# Run with startup checks
CMD ["./startup.sh"]
