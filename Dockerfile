# Use an official Python runtime as a parent image
FROM python:3.8

# Set the working directory in the container
WORKDIR /app

# Update the package lists and install sqlite3
RUN apt-get update && apt-get install -y sqlite3

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir flask>=2.0 flask_cors python-dotenv flask_jwt_extended
RUN pip install --no-cache-dir --upgrade openai


# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define a volume for persistent data
VOLUME /data

# Run app.py when the container launches
CMD ["python", "main.py"]
