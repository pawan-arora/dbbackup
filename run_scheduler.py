#!/usr/bin/env python3

from scheduler import Scheduler
from state_manager import StateManager
from utils.logger import logger
import time

if __name__ == "__main__":
    state_mgr = StateManager()
    scheduler = Scheduler(state_mgr)
    logger.info("Scheduler started. Waiting for scheduled tasks...")
    while True:
        time.sleep(60)