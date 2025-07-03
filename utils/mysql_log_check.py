import os
from utils.docker_helper import find_running_container, run_command_with_fallback
import tempfile

def is_binary_logging_enabled(config):
    my = config['mysql']
    file_path = tempfile.mktemp(suffix="_log_bin_status.txt")
    # file_path = "/tmp/log_bin_status.txt"
    cmd = [
        "mysql",
        "-h", my["host"],
        "-P", str(my["port"]),
        "-u", my["user"],
        f"-p{my['password']}",
        "-e", "SHOW VARIABLES LIKE 'log_bin';"
    ]

    container = find_running_container("mysql")
    try:
        if run_command_with_fallback(cmd, file_path, fallback_container=container):
            with open(file_path) as f:
                for line in f:
                    if "log_bin" in line and "ON" in line.upper():
                        return True
    except Exception as e:
        print(f"[ERROR] Failed to check binary logging: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return False
