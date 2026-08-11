# 1. Start with an official, lightweight Python base image
FROM python:3.11-slim

# 2. Set the working directory inside the container virtual machine
WORKDIR /code

# 3. Copy our requirements configuration file first (to leverage Docker build caching)
COPY requirements.txt /code/requirements.txt

# 4. Install the required libraries inside the container system
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 5. Copy our actual application code folder into the container
COPY ./app /code/app

# 6. Expose the port number FastAPI will listen on
EXPOSE 8000

# 7. The execution command to boot up Uvicorn when the container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
