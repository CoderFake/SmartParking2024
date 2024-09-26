FROM python:3.10-slim
ENV PYTHONUNBUFFERED 1

# Create directory
RUN mkdir -p /home/smartparking/api

# Set work directory
WORKDIR /home/smartparking/api

# Install dependencies
ADD ../requirements.txt /home/smartparking/api

RUN apt-get update \
    && pip3 install --upgrade pip \
    && pip3 install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --autoremove gcc

# Copy project files
ADD . /home/smartparking/api

EXPOSE 8001
