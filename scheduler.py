import threading
import time
from datetime import datetime
from backup import mysql_backup, postgres_backup
from s3 import uploader
from utils.logger import logger
from utils.email_notifier import EmailNotifier
from utils.logger import disable_console_logging
from datetime import datetime, timedelta

class Scheduler:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.schedules = self.state_manager.load_schedules()
        self.threads = {}  # db -> Thread
        self.lock = threading.Lock()
        self.emailer = None

        # Start any active schedules from saved state
        for db, details in self.schedules.items():
            if not details.get("stopped", False) and details.get("count", 0) > details.get("completed", 0):
                self._start_thread(db, details)

    def _start_thread(self, db, details):
        if db in self.threads and self.threads[db].is_alive():
            logger.info(f"Schedule for {db} already running.")
            return

        thread = threading.Thread(target=self._run_schedule, args=(db,))
        thread.daemon = True
        self.threads[db] = thread
        thread.start()
        logger.info(f"Started schedule thread for {db}.")

    def _run_schedule(self, db):
        # Disable console logs for scheduler thread
        # disable_console_logging()
        while True:
            with self.lock:
                schedule = self.schedules.get(db)
                if not schedule or schedule.get("stopped", False):
                    logger.info(f"Schedule for {db} stopped or removed.")
                    break

                count = schedule.get("count", 0)
                completed = schedule.get("completed", 0)
                if completed >= count:
                    logger.info(f"Schedule for {db} completed all backups.")
                    schedule["stopped"] = True
                    self.state_manager.save_schedules(self.schedules)
                    break

                gap_days = schedule.get("gap", 1)
                last_backup_str = schedule.get("last_backup_time")
                if last_backup_str:
                    last_backup_time = datetime.strptime(last_backup_str, "%Y-%m-%d %H:%M:%S")
                    next_allowed_time = last_backup_time + timedelta(days=gap_days)
                    now = datetime.now()
                    time.sleep(60)
                    # if now < next_allowed_time:
                    #     sleep_seconds = (next_allowed_time - now).total_seconds()
                    #     logger.info(f"Next backup for {db} scheduled in {int(sleep_seconds)} seconds.")
                    #     time.sleep(sleep_seconds)

                # Prepare backup params
                config = schedule.get("config")
                tables = schedule.get("tables")
                schema_only = schedule.get("schema_only", False)
                data_only = schedule.get("data_only", False)
                compress = schedule.get("compress", False)
                notify = schedule.get("notify")

            logger.info(f"Starting scheduled backup {completed + 1} of {count} for {db}")

            try:
                date_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                if db == 'postgres':
                    file_path = postgres_backup.backup(config, date_str, tables.split(',') if tables else None,
                                                    schema_only, data_only, compress)
                elif db == 'mysql':
                    file_path = mysql_backup.backup(config, date_str, tables.split(',') if tables else None,
                                                    schema_only, data_only, compress)
                else:
                    logger.error(f"Unsupported DB {db} in scheduler.")
                    break

                uploader.upload_to_s3(file_path, config)
                logger.info(f"Uploaded backup file {file_path} for scheduled backup {completed + 1} of {count}")

                if notify:
                    self.emailer = EmailNotifier(config)
                    threading.Thread(target=self.emailer.notify_in_background,
                                    args=(notify, [file_path], db, 1, True), daemon=True).start()

                # Save updated state
                with self.lock:
                    schedule["completed"] = completed + 1
                    schedule["last_backup_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.state_manager.save_schedules(self.schedules)

            except Exception as e:
                logger.error(f"Scheduled backup failed for {db}: {e}")
                break

    def add_schedule(self, db, count, gap, tables, schema_only, data_only, compress, notify):
        with self.lock:
            # If schedule exists, stop previous schedule thread first
            if db in self.schedules and not self.schedules[db].get("stopped", False):
                logger.info(f"Stopping existing schedule for {db}")
                self.schedules[db]["stopped"] = True
                self.state_manager.save_schedules(self.schedules)

            # Add new schedule
            config = self.state_manager.load_config()
            self.schedules[db] = {
                "count": count,
                "gap": gap,
                "tables": tables,
                "schema_only": schema_only,
                "data_only": data_only,
                "compress": compress,
                "notify": notify,
                "completed": 0,
                "stopped": False,
                "config": config
            }
            self.state_manager.save_schedules(self.schedules)
            self._start_thread(db, self.schedules[db])

    def cancel_schedule(self, db):
        with self.lock:
            if db in self.schedules and not self.schedules[db].get("stopped", False):
                self.schedules[db]["stopped"] = True
                self.state_manager.save_schedules(self.schedules)
                logger.info(f"Cancelled schedule for {db}")
                return True
        return False

    def get_active_schedules(self):
        with self.lock:
            return {db: details for db, details in self.schedules.items() if not details.get("stopped", False)}

if __name__ == "__main__":
    from state_manager import StateManager
    state_mgr = StateManager()
    scheduler = Scheduler(state_mgr)
    logger.info("Scheduler started. Waiting for scheduled tasks...")
    # Block forever
    while True:
        time.sleep(60)