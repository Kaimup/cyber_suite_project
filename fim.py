# fim/fim_hash_monitor.py
import os
import hashlib
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

WATCHED_DIR = "./test_folder"        # Directory to monitor
LOG_FILE = "./fim/file_log.json"     # Keep log file outside WATCHED_DIR
HASH_FILE = "./fim/file_hashes.json" # Stores last known hashes

# Ensure log and hash files exist
for file in [LOG_FILE, HASH_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f if file == HASH_FILE else [], f, indent=2)

def hash_file(file_path):
    """Return SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        return None  # File deleted before hashing

class MonitorHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        # Load existing hashes
        with open(HASH_FILE, "r") as f:
            try:
                self.hashes = json.load(f)
            except json.JSONDecodeError:
                self.hashes = {}

    def save_hashes(self):
        with open(HASH_FILE, "w") as f:
            json.dump(self.hashes, f, indent=2)

    def log_event(self, event_type, file_path, file_hash=None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "file": file_path,
        }
        if file_hash:
            log_entry["hash"] = file_hash

        # Append to log file
        with open(LOG_FILE, "r+") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(log_entry)
            f.seek(0)
            json.dump(data, f, indent=2)

        print(log_entry)

    def on_created(self, event):
        if not event.is_directory:
            file_hash = hash_file(event.src_path)
            self.hashes[event.src_path] = file_hash
            self.log_event("CREATED", event.src_path, file_hash)
            self.save_hashes()

    def on_deleted(self, event):
        if not event.is_directory:
            # Remove hash
            if event.src_path in self.hashes:
                del self.hashes[event.src_path]
                self.save_hashes()
            self.log_event("DELETED", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            new_hash = hash_file(event.src_path)
            old_hash = self.hashes.get(event.src_path)
            if new_hash and new_hash != old_hash:
                self.hashes[event.src_path] = new_hash
                self.log_event("MODIFIED", event.src_path, new_hash)
                self.save_hashes()

if __name__ == "__main__":
    os.makedirs(WATCHED_DIR, exist_ok=True)
    event_handler = MonitorHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=True)
    observer.start()
    print(f"Monitoring {WATCHED_DIR}... Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping monitor...")
        observer.stop()
    observer.join()
