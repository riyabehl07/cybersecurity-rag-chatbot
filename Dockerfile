# Use a stable, official Python 3.11 image as our base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies for C/C++ extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies with extended timeout
RUN pip install --no-cache-dir --default-timeout=600 -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose port 5000 so we can access the web app
EXPOSE 5000

# The command to run when the container starts
CMD ["python", "app.py"]
