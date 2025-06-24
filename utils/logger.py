import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "backup.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Create logger object
logger = logging.getLogger("dbbackup")
logger.setLevel(logging.INFO)

# Rotating File Handler (unchanged)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console Handler (new)
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Add console by default (for CLI interactive)
console_enabled = True
logger.addHandler(console_handler)

# Utility functions to toggle console logging dynamically
def disable_console_logging():
    global console_enabled
    if console_enabled:
        logger.removeHandler(console_handler)
        console_enabled = False

def enable_console_logging():
    global console_enabled
    if not console_enabled:
        logger.addHandler(console_handler)
        console_enabled = True
