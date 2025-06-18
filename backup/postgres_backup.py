import subprocess
import os
import gzip
import shutil
from utils.logger import logger

def backup(config, date, tables=None, schema_only=False, data_only=False, compress=False):
    pg = config["postgres"]
    db = pg["database"]
    file_name = f"postgres_backup_{date}.sql"
    file_path = os.path.join("/tmp", file_name)

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

    with open(file_path, "w") as f:
        env = os.environ.copy()
        env["PGPASSWORD"] = pg["password"]
        result = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.PIPE)

    if result.returncode != 0:
        logger.error(f"Backup failed: {result.stderr.decode()}")
        raise Exception("pg_dump failed")

    logger.info(f"Backup successful: {file_path}")

    if compress:
        compressed_path = file_path + ".gz"
        with open(file_path, 'rb') as f_in, gzip.open(compressed_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        logger.info(f"Compressed to: {compressed_path}")
        return compressed_path

    return file_path
