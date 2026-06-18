FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies required for mysqlclient and potential ML wheels
RUN apt-get update && apt-get install -y \
    pkg-config \
    gcc \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . /app/
RUN chmod +x /app/scripts/docker-entrypoint.sh

# Expose port 8000
EXPOSE 8000

# Start ASGI server
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "mlhospital.asgi:application"]
