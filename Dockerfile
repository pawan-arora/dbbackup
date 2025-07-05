FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only source code, NOT configs or logs
COPY cli.py scheduler.py config_loader.py state_manager.py ./
COPY backup ./backup
COPY s3 ./s3
COPY utils ./utils
COPY cleanup ./cleanup

# Create logs directory inside image (empty initially)
RUN mkdir -p logs

# Rename cli.py to dbbackup and make it executable
# Rename cli.py to dbbackup, fix line endings, make it executable, and symlink it
RUN mv cli.py dbbackup \
    && sed -i 's/\r$//' dbbackup \
    && chmod +x dbbackup \
    && ln -s /app/dbbackup /usr/local/bin/dbbackup

# Default CMD: start scheduler on container start
CMD ["python", "scheduler.py"]
