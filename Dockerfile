# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port Gunicorn will listen on
EXPOSE 10000

# Start the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]