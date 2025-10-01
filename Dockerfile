# Use official Python image as base
FROM python:3.10-slim

# Set working directory in the container
WORKDIR /app

# Copy all project files into the container
COPY . .

# Install any needed dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 80 (Flask will run on this inside the container)
EXPOSE 80

# Set environment variables for Flask (optional)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=80

# Run the Flask app
CMD ["python", "app.py"]
