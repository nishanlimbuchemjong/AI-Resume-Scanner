# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port (Flask default is 5000)
EXPOSE 5000

# Command to run the app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
