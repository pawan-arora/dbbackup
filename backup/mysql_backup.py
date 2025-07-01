import os
import gzip
import shutil
import subprocess
from utils.logger import logger
from pathlib import Path
from utils.docker_helper import find_running_container, run_command_with_fallback
from datetime import datetime

def backup(config, date, tables=None, schema_only=False, data_only=False, compress=False):
    my = config["mysql"]
    db = my["database"]
    tmp_dir = Path(os.getenv("TMP", os.getenv("TEMP", "/tmp")))
    backup_filename = f"mysql_backup_{date}.sql"
    file_path = tmp_dir / backup_filename

    cmd = [
        "mysqldump",
        "-h", my["host"],
        "-P", str(my["port"]),
        "-u", my["user"],
        f"-p{my['password']}",
        db
    ]

    if tables:
        cmd += tables
    if schema_only:
        cmd.append("--no-data")
    if data_only:
        cmd.append("--no-create-info")

    # Find fallback Docker container (optional)
    container = find_running_container("mysql")

    # Run mysqldump with fallback
    success = run_command_with_fallback(cmd, file_path, fallback_container=container)

    if not success:
        raise Exception("mysqldump failed")

    logger.info(f"Backup successful: {file_path}")

    if compress:
        compressed_path = file_path.with_suffix(file_path.suffix + ".gz")
        with open(file_path, 'rb') as f_in, gzip.open(compressed_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        logger.info(f"Compressed to: {compressed_path}")
        return compressed_path

    return file_path

def backup_incremental(config):
    my = config["mysql"]
    log_file, _ = get_last_binlog_position(config)
    binlog_file = f"mysql_binlog_backup_{date}.sql"
    output_path = os.path.join("/tmp", binlog_file)

    cmd = [
        "mysqlbinlog",
        "--read-from-remote-server",
        f"--host={my['host']}",
        f"--port={my['port']}",
        f"--user={my['user']}",
        f"--password={my['password']}",
        log_file
    ]

    container = find_running_container("mysql")

    # Run mysqldump with fallback
    success = run_command_with_fallback(cmd, output_path, fallback_container=container)

    if not success:
        raise Exception("mysqldump failed")

    logger.info(f"Backup successful: {output_path}")

    return output_path

def get_last_binlog_position(config):
    my = config["mysql"]
    file_path = "/tmp/show_master_status.txt"
    cmd = [
        "mysql",
        f"-h{my['host']}",
        f"-P{my['port']}",
        f"-u{my['user']}",
        f"-p{my['password']}",
        "-e", "SHOW MASTER STATUS;"
    ]

    container = find_running_container("mysql")
    success = run_command_with_fallback(cmd, file_path, fallback_container=container)

    if not success:
        raise Exception("SHOW MASTER STATUS failed")

    try:
        with open(file_path) as f:
            lines = f.read().strip().split('\n')
            if len(lines) < 2:
                raise Exception("Unexpected result from SHOW MASTER STATUS")

            parts = lines[1].split('\t')
            return parts[0], parts[1]  # log_file, log_pos
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)