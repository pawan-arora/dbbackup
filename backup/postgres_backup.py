import subprocess
import os
import gzip
import shutil
from pathlib import Path
from utils.logger import logger
from utils.docker_helper import find_running_container, run_command_with_fallback

def backup(config, date, tables=None, schema_only=False, data_only=False, compress=False):
    pg = config["postgres"]
    db = pg["database"]
    tmp_dir = Path(os.getenv("TMP", os.getenv("TEMP", "/tmp")))
    backup_filename = f"postgres_backup_{date}.sql"
    file_path = tmp_dir / backup_filename

    cmd = [
        "pg_dump",
        "-h", pg["host"],
        "-p", str(pg["port"]),
        "-U", pg["user"],
        "-d", db
    ]

    if tables:
        for table in tables:
            cmd += ["-t", table]
    if schema_only:
        cmd.append("--schema-only")
    if data_only:
        cmd.append("--data-only")

    # Set PGPASSWORD for authentication
    env = os.environ.copy()
    env["PGPASSWORD"] = pg["password"]

    # Detect running postgres Docker container
    container = find_running_container("postgres")

    # Run pg_dump with fallback logic
    success = run_command_with_fallback(cmd, file_path, env=env, fallback_container=container)

    if not success:
        raise Exception("pg_dump failed")

    logger.info(f"Backup successful: {file_path}")

    if compress:
        compressed_path = file_path.with_suffix(file_path.suffix + ".gz")
        with open(file_path, 'rb') as f_in, gzip.open(compressed_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        logger.info(f"Compressed to: {compressed_path}")
        return compressed_path

    return file_path
