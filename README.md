# Smart Parking

<img src="https://raw.githubusercontent.com/CoderFake/SmartParking/main/smartparking/static/webapp/assets/img/sp-logo-image.png?token=GHSAT0AAAAAACQDYSZCM4LZ3XOCVZVRBQRGZWBUJAQ" alt="Smart Parking Logo" width="180" height="180">


## Overview
- **Python Version:**  = 3.12
- The configuration file is located at **SmartPaking/.env SmartPaking/admin.env and SmartPaking/api.env **.
- You can override environment-specific settings by placing a configuration file for the local environment in **.env files**.
    - **Note:** Do not commit this file.

## Development Environment Setup

### Start the project with the following commands:

	```bash
	$ docker-compose up -d
##### If you need to recreate the Docker image, for example, after adding libraries, stop the container, remove the original image, and restart.

##### Find the image ID of the smart_parking image from the image list obtained with docker image ls.

##### Delete the corresponding image using docker image rm.
	```bash
	$ docker-compose down
	$ docker image ls
	REPOSITORY                           TAG             IMAGE ID       CREATED         SIZE
	smart_parking                          develop         [IMAGE ID]    6 days ago      826MB

##### Delete each image
	```bash
	$ docker image rm [IMAGE ID]


##### Delete all images
	```bash
	$ docker-compose down
	$ docker rm -f  $(docker ps -a -q)
	$ docker rmi $(docker images -q)

### Running Without Docker

If you prefer not to use Docker, follow these steps to set up the environment and run the application:

#### Prerequisites

- Ensure you have Python = 3.12 installed on your system.
- Install the required Python packages listed in `requirements.txt`.

### Setting Up the Environment
#### **Create a Postgres database**:

##### Create smart_parking_db
** First, you need to make sure that PostgreSQL is installed on your computer. **
- You can download PostgreSQL from the official PostgreSQL page and follow the installation instructions.
- Using psql (PostgreSQL CLI)
Step 1: Open Command Prompt (CMD) , PowerShell on Windows or Termial on Mac, Lilux
Step 2: Connect to PostgreSQL

##### To connect to PostgreSQL, use the following command:

	```console
	$ psql -U postgres
	$ CREATE DATABASE smart_parking_db;

#### **Create a virtual environment**:
	```console smartparking
	$ cd smartparking
	$ python -m venv .venv
	$ source .venv/bin/activate       - lilux
	$ .venv\Scripts\activate           - window
	$ pip install -r requiements.txt
	$ python manage.py makemigration
	$ python manage.py migrate
	$ python manage.py runserver

	console api
	$ cd api
	$ python -m venv .venv
	$ source .venv/bin/activate       - lilux
	$ .venv\Scripts\activate          - window
	$ pip install -r requiements.txt
	$ uvicorn main:app --host 0.0.0.0 --port 8001 --reload

### After clone repo and install requirement packages, execute command to install git hook pre-commit install


