# fim/fim_fixed.py
import os
import hashlib
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

WATCHED_DIR = "./test_folder"          # Directory to monitor
LOG_FILE = "./fim/file_log.json"       # Ensure this is NOT inside WATCHED_DIR

# Ensure log file exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        json.dump([], f)

def hash_file(file_path):
    """Return SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

class MonitorHandler(FileSystemEventHandler):
    def log_event(self, event_type, file_path):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "file": file_path
        }
        # Read existing logs
        try:
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []

        data.append(log_entry)

        # Write back to single log file
        with open(LOG_FILE, "w") as f:
            json.dump(data, f, indent=2)

        print(log_entry)

    def on_created(self, event):
        if not event.is_directory:
            self.log_event("CREATED", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.log_event("DELETED", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.log_event("MODIFIED", event.src_path)

if __name__ == "__main__":
    os.makedirs(WATCHED_DIR, exist_ok=True)
    event_handler = MonitorHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=True)
    observer.start()
    print(f"Monitoring {WATCHED_DIR}...")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
