# Using a slim Python base image
FROM python:3.11-slim

# Working directory in the container
WORKDIR /app

# Installing the necessary dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copying the rest of the application
COPY . .

# Exposing the port for FastAPI to run on
EXPOSE 8000

# Running the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
