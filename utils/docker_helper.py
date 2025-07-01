import subprocess
import shutil
from utils.logger import logger


def command_exists(cmd):
    return shutil.which(cmd) is not None


def find_running_container(keyword):
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}} {{.Image}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in result.stdout.strip().splitlines():
            name, image = line.split(maxsplit=1)
            if keyword.lower() in image.lower():
                return name
    except Exception as e:
        logger.warning(f"Could not check Docker containers: {e}")
    return None


def run_command_with_fallback(cmd, file_path, fallback_container=None):
    """Try to run command directly; if fails, retry via Docker exec"""

    try:
        if fallback_container:
            docker_cmd = ["docker", "exec", fallback_container] + cmd
            with open(file_path, "w") as f:
                result = subprocess.run(docker_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        else:
            with open(file_path, "w") as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False

    if result.returncode == 0:
        return True

    logger.error(f"Command failed: {result.stderr}")
    return False

def run_command_with_fallback_without_file(cmd, fallback_container=None):
    try:
        if fallback_container:
            docker_cmd = ["docker", "exec", fallback_container] + cmd
            result = subprocess.run(docker_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return None

    if result.returncode == 0:
        return result.stdout

    logger.error(f"Command failed: {result.stderr}")
    return None
