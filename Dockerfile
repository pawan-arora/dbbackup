FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy everything into the image
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run CLI tool by default — override if needed
ENTRYPOINT ["python", "cli.py"]
