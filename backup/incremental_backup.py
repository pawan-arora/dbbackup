# backup/incremental_backup.py

import os
import subprocess
from datetime import datetime
from utils.logger import logger
from utils.docker_helper import run_command_with_fallback_without_file, find_running_container

def get_last_binlog_position(config):
    my = config["mysql"]
    cmd = [
        "mysql",
        f"-h{my['host']}",
        f"-P{my['port']}",
        f"-u{my['user']}",
        f"-p{my['password']}",
        "-e", "SHOW BINARY LOG STATUS;"
    ]

    # Find fallback Docker container (optional)
    container = find_running_container("mysql")

    # Run mysqldump with fallback
    result = run_command_with_fallback_without_file(cmd, fallback_container=container)

    if not result:
        raise Exception("SHOW MASTER STATUS failed")

    lines = result.strip().split('\n')
    if len(lines) < 2:
        raise Exception("Unexpected result from SHOW BINARY LOG STATUS")

    header = lines[0].split('\t')
    values = lines[1].split('\t')

    binlog_file = values[header.index("File")]
    position = values[header.index("Position")]
    return binlog_file, position  # log_file, log_pos

def mysql_incremental_backup(config, date):
    log_file, _ = get_last_binlog_position(config)
    binlog_file = f"mysql_binlog_backup_{date}.sql"
    output_path = os.path.join("/tmp", binlog_file)

    my = config["mysql"]
    container = find_running_container("mysql")
    if container:
        cmd = [
            "docker", "exec", container,
            "mysqlbinlog",
            f"--read-from-remote-server",
            f"--host={my['host']}",
            f"--port={my['port']}",
            f"--user={my['user']}",
            f"--password={my['password']}",
            log_file
        ]
        # Note: With docker exec, direct output redirection to file_path is not straightforward
        # So we run the command and capture output
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error(f"mysqlbinlog failed: {result.stderr.decode()}")
            raise Exception("Incremental backup failed")
        with open(output_path, "wb") as f:
            f.write(result.stdout)
    else:
        cmd = [
            "mysqlbinlog",
            "--read-from-remote-server",
            f"--host={my['host']}",
            f"--port={my['port']}",
            f"--user={my['user']}",
            f"--password={my['password']}",
            log_file
        ]
        with open(output_path, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.error(f"mysqlbinlog failed: {result.stderr.decode()}")
                raise Exception("Incremental backup failed")

    logger.info(f"Incremental MySQL backup saved to {output_path}")
    return output_path

def postgres_incremental_backup(config):
    pg = config["postgres"]
    now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    wal_dir = pg.get("wal_archive_dir", "/var/lib/postgresql/wal_archive")
    output = Path(os.getenv("TMP", os.getenv("TEMP", "/tmp"))) / f"pg_inc_backup_{now}.tar.gz"

    if not os.path.isdir(wal_dir):
        raise Exception(f"WAL archive directory not found: {wal_dir}")

    logger.info(f"Archiving WAL files from {wal_dir}")
    subprocess.run(["tar", "-czf", str(output), "-C", wal_dir, "."], check=True)
    logger.info(f"Created incremental archive: {output}")
    return output
