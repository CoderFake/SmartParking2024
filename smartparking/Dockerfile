# Base image
FROM python:3.12

# Create directory
RUN mkdir -p /home/smartparking/smartparking

# Set work directory
WORKDIR /home/smartparking/smartparking

# Install dependencies
ADD requirements.txt /home/smartparking/smartparking
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
ADD . /home/smartparking/smartparking

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
