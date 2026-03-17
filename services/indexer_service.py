import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

logger = logging.getLogger(__name__)

class BrainIndexerHandler(FileSystemEventHandler):
    def __init__(self, memory_service):
        self.memory_service = memory_service
        self.valid_exts = {'.txt', '.md', '.py', '.js', '.html', '.css', '.pdf'}

    def on_created(self, event):
        if not event.is_directory:
            self._process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._process_file(event.src_path)

    def _process_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self.valid_exts:
            logger.info(f"BrainIndexer: Autodetected new/modified file: {file_path}")
            # Schedule ingestion in MemoryService
            try:
                self.memory_service.ingest_document(file_path)
            except Exception as e:
                logger.error(f"BrainIndexer: Error ingesting {file_path}: {e}")

class BrainIndexerService:
    """
    Background service that monitors the filesystem and automatically
    ingests new knowledge into Jarvis's brain.
    """
    def __init__(self, memory_service, watch_paths=None):
        self.memory_service = memory_service
        if watch_paths is None:
            # Default to Documents and Desktop
            home = str(Path.home())
            self.watch_paths = [
                os.path.join(home, "Documents"),
                os.path.join(home, "Desktop")
            ]
        else:
            self.watch_paths = watch_paths
            
        self.observer = Observer()
        self.handler = BrainIndexerHandler(self.memory_service)
        self.running = False

    def start(self):
        for path in self.watch_paths:
            if os.path.exists(path):
                self.observer.schedule(self.handler, path, recursive=True)
                logger.info(f"BrainIndexer: Watching {path}")
        
        self.observer.start()
        self.running = True

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.running = False
