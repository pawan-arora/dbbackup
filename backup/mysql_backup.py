import subprocess
import os
import gzip
import shutil
from utils.logger import logger
from pathlib import Path

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

    with open(file_path, "w") as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)

    if result.returncode != 0:
        logger.error(f"Backup failed: {result.stderr.decode()}")
        raise Exception("mysqldump failed")

    logger.info(f"Backup successful: {file_path}")

    if compress:
        compressed_path = file_path + ".gz"
        with open(file_path, 'rb') as f_in, gzip.open(compressed_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        logger.info(f"Compressed to: {compressed_path}")
        return compressed_path

    return file_path
