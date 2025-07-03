import json
import os
import threading

CONFIG_FILE = "config.yaml"

class StateManager:
    def __init__(self):
        self.state_file = os.path.join("config", "schedules.json")
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        self.lock = threading.Lock()

    def load_schedules(self):
        if not os.path.exists(self.state_file):
            return {}
        with open(self.state_file, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return {}

    def save_schedules(self, schedules):
        with self.lock:
            with open(self.state_file, "w") as f:
                json.dump(schedules, f, indent=4)

    def load_config(self):
        import yaml
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f)
