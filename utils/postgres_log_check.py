import subprocess
from utils.logger import logger
from utils.docker_helper import find_running_container

def is_wal_archiving_enabled(config):
    pg = config["postgres"]
    container = find_running_container("postgres")

    query = "SHOW wal_level; SHOW archive_mode;"
    base_cmd = [
        "psql",
        "-U", pg["user"],
        "-d", pg["database"],
        "-c", query
    ]

    if container:
        cmd = ["docker", "exec", container] + base_cmd
    else:
        cmd = [
            "psql",
            "-h", pg["host"],
            "-p", str(pg["port"]),
            "-U", pg["user"],
            "-d", pg["database"],
            "-c", query
        ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            logger.error(f"Failed to query PostgreSQL WAL settings: {result.stderr.strip()}")
            return False

        output = result.stdout.lower()
        return "replica" in output and "on" in output

    except Exception as e:
        logger.error(f"PostgreSQL WAL check failed: {e}")
        return False
