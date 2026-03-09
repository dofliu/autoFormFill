"""
File Watcher Service — monitors directories for file changes and triggers auto-indexing.

Uses watchdog for OS-level file system events, with a debounce mechanism to avoid
re-indexing files that are still being written.

Architecture:
  1. watchdog Observer watches configured directories
  2. Events are debounced (wait for file to stabilize)
  3. Stable events are queued for async processing
  4. Background task picks up queue items and calls indexing_service

Threading model:
  - watchdog callbacks run on an OS thread (NOT the asyncio event loop)
  - We use asyncio.run_coroutine_threadsafe() to safely schedule coroutines
    from the OS thread onto the event loop
  - The _pending dict is accessed from both threads; Python's GIL makes
    dict operations atomically safe in CPython

Lifecycle:
  - start() — called from main.py lifespan (startup)
  - stop()  — called from main.py lifespan (shutdown)
"""
import asyncio
import logging
import os
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import settings

logger = logging.getLogger(__name__)

# Debounce: wait this many seconds after last modification before indexing
DEBOUNCE_SECONDS = 3.0


class _IndexingEventHandler(FileSystemEventHandler):
    """Watchdog handler that collects file events into an async queue.

    Implements debouncing: tracks the last modification time for each file
    and only queues the file once it has been stable for DEBOUNCE_SECONDS.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        super().__init__()
        self._loop = loop
        self._queue = queue
        self._supported_exts = settings.get_supported_extensions()
        # Track pending files: file_path -> last_event_time
        # Accessed from both watchdog thread and asyncio coroutines;
        # CPython's GIL ensures dict get/set are atomic.
        self._pending: dict[str, float] = {}

    def _is_supported(self, path: str) -> bool:
        """Check if file extension is in supported set."""
        ext = Path(path).suffix.lower()
        return ext in self._supported_exts

    def _schedule_debounced(self, event_type: str, src_path: str):
        """Thread-safe: schedule a debounced async enqueue on the event loop."""
        if not self._is_supported(src_path):
            return
        # Record the event time for debouncing
        self._pending[src_path] = time.time()
        # Use run_coroutine_threadsafe — the correct way to schedule coroutines
        # from a non-asyncio thread
        asyncio.run_coroutine_threadsafe(
            self._debounce_and_enqueue(event_type, src_path),
            self._loop,
        )

    def _schedule_immediate(self, event_type: str, src_path: str):
        """Thread-safe: immediately enqueue (no debounce) for deletions."""
        if not self._is_supported(src_path):
            return
        self._pending.pop(src_path, None)
        asyncio.run_coroutine_threadsafe(
            self._queue.put((event_type, src_path)),
            self._loop,
        )

    async def _debounce_and_enqueue(self, event_type: str, src_path: str):
        """Wait for file to stabilize, then enqueue for indexing."""
        await asyncio.sleep(DEBOUNCE_SECONDS)
        # Check if this file has been modified again during the wait
        last_time = self._pending.get(src_path, 0)
        if time.time() - last_time < DEBOUNCE_SECONDS - 0.1:
            # Another event came in during our wait; skip this one
            return
        # File is stable, enqueue it
        self._pending.pop(src_path, None)
        await self._queue.put((event_type, src_path))

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self._schedule_debounced("created", event.src_path)

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self._schedule_debounced("modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            # Deletions are immediate — no debounce needed
            self._schedule_immediate("deleted", event.src_path)

    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            # Treat as delete old + create new
            if hasattr(event, "dest_path"):
                self._schedule_immediate("deleted", event.src_path)
                self._schedule_debounced("created", event.dest_path)


class FileWatcher:
    """Manages watchdog observers and the async indexing worker.

    Usage:
        watcher = FileWatcher()
        await watcher.start()   # in lifespan startup
        ...
        await watcher.stop()    # in lifespan shutdown
    """

    def __init__(self):
        self._observer: Observer | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._scan_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start watching configured directories."""
        watch_dirs = settings.get_watch_dirs()
        if not watch_dirs:
            logger.info("No watch directories configured (WATCH_DIRS is empty)")
            return

        loop = asyncio.get_running_loop()
        handler = _IndexingEventHandler(loop, self._queue)

        self._observer = Observer()
        for dir_path in watch_dirs:
            if os.path.isdir(dir_path):
                self._observer.schedule(handler, dir_path, recursive=True)
                logger.info(f"Watching directory: {dir_path}")
            else:
                logger.warning(f"Watch directory not found, skipping: {dir_path}")

        self._observer.daemon = True
        self._observer.start()
        self._running = True

        # Start the async worker that processes queued events
        self._worker_task = asyncio.create_task(self._process_queue())

        # Run initial scan of all watched directories (tracked for cleanup)
        self._scan_task = asyncio.create_task(self._initial_scan(watch_dirs))

        logger.info(f"File watcher started, monitoring {len(watch_dirs)} directories")

    async def stop(self):
        """Stop watching and clean up.

        Note: any events remaining in the queue are discarded. Files modified
        just before shutdown will be picked up by the next startup's initial scan.
        """
        self._running = False

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        # Cancel the initial scan if still running
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
            self._scan_task = None

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        logger.info("File watcher stopped")

    async def _initial_scan(self, watch_dirs: list[str]):
        """Perform initial full scan of all watched directories on startup."""
        from app.services.indexing_service import scan_directory

        logger.info("Starting initial directory scan...")
        for dir_path in watch_dirs:
            if os.path.isdir(dir_path):
                try:
                    stats = await scan_directory(dir_path)
                    logger.info(f"Initial scan of {dir_path}: {stats}")
                except Exception as e:
                    logger.error(f"Initial scan failed for {dir_path}: {e}")
        logger.info("Initial directory scan complete")

    async def _process_queue(self):
        """Background worker: consume events from the queue and trigger indexing."""
        from app.services.indexing_service import index_file, remove_file

        logger.info("Indexing worker started")
        while self._running:
            try:
                event_type, file_path = await asyncio.wait_for(
                    self._queue.get(), timeout=2.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                if event_type == "deleted":
                    result = await remove_file(file_path)
                else:
                    # created or modified → index
                    result = await index_file(file_path)

                action = result.get("action", "unknown") if isinstance(result, dict) else "unknown"
                logger.info(f"Watcher event [{event_type}]: {file_path} -> {action}")
            except Exception as e:
                logger.error(f"Watcher indexing error for {file_path}: {e}")

        logger.info("Indexing worker stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        """Return watcher status for API."""
        return {
            "running": self._running,
            "watch_dirs": settings.get_watch_dirs(),
            "queue_size": self._queue.qsize(),
            "supported_extensions": list(settings.get_supported_extensions()),
        }


# Module-level singleton
file_watcher = FileWatcher()
