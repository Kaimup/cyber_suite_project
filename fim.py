# fim.py
import os
import hashlib
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# CHANGE ONLY THIS
WATCHED_DIR = "/YOUR_DIRECTORY"

# Log + hash files (kept in same dir as script, outside WATCHED_DIR ideally)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "file_log.json")
HASH_FILE = os.path.join(BASE_DIR, "file_hashes.json")

# Ignore these files so we don’t get infinite loops
IGNORE_FILES = {LOG_FILE, HASH_FILE}

def ensure_files():
    """Make sure log and hash files exist."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f, indent=2)
    if not os.path.exists(HASH_FILE):
        with open(HASH_FILE, "w") as f:
            json.dump({}, f, indent=2)

def hash_file(file_path):
    """Return SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        return None

class MonitorHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
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

        with open(LOG_FILE, "r+") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(log_entry)
            f.seek(0)
            json.dump(data, f, indent=2)

        print(log_entry)

    def should_ignore(self, path):
        return path in IGNORE_FILES

    def on_created(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            file_hash = hash_file(event.src_path)
            self.hashes[event.src_path] = file_hash
            self.log_event("CREATED", event.src_path, file_hash)
            self.save_hashes()

    def on_deleted(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            if event.src_path in self.hashes:
                del self.hashes[event.src_path]
                self.save_hashes()
            self.log_event("DELETED", event.src_path)

    def on_modified(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            new_hash = hash_file(event.src_path)
            old_hash = self.hashes.get(event.src_path)
            if new_hash and new_hash != old_hash:
                self.hashes[event.src_path] = new_hash
                self.log_event("MODIFIED", event.src_path, new_hash)
                self.save_hashes()

if __name__ == "__main__":
    os.makedirs(WATCHED_DIR, exist_ok=True)
    ensure_files()

    event_handler = MonitorHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=True)
    observer.start()
    print(f"Monitoring {WATCHED_DIR}... Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
