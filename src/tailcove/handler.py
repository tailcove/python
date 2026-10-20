from __future__ import annotations

import logging
import queue
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .context import extra_context
from .exceptions import format_exception
from .levels import normalize_level
from .transport import send_batch

DEFAULT_ENDPOINT = "https://ingest.tailcove.dev/api/v1/logs"
DEFAULT_BATCH_SIZE = 50
DEFAULT_BATCH_SECONDS = 2.0
DEFAULT_TIMEOUT = 2.0
DEFAULT_TRACE_LIMIT = 10

# Queue item kinds. A plain string tag plus payload, rather than subclasses,
# keeps the background loop's dispatch a single if/elif chain.
_LOG = "log"
_FLUSH = "flush"
_CLOSE = "close"


class TailcoveHandler(logging.Handler):
    """
    Batches records and ships them to a Tailcove source's ingest endpoint on
    a background thread — up to `batch_size` lines or `batch_seconds`,
    whichever comes first, matching the wire contract and thresholds of the
    tailcove/laravel and @tailcove/node clients (see the log-ingestion
    skill). Never raises into the host app: `emit()` catches its own
    failures and reports them via `self.handleError()`, the stdlib
    `Handler` convention; delivery failures on the background thread are
    caught and printed to stderr rather than propagated anywhere.

    Flushing at interpreter exit is handled by the stdlib itself: every
    `logging.Handler` is registered in `logging._handlerList`, and the
    `logging` module registers its own `atexit` hook (`logging.shutdown`)
    that calls `flush()` then `close()` on every handler. Subclassing
    `Handler` and implementing `close()` to drain the queue is therefore
    sufficient — no separate `atexit.register()` call is needed here, and
    adding one would risk a double flush racing the stdlib's own.
    """

    def __init__(
        self,
        token: str,
        endpoint: str = DEFAULT_ENDPOINT,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_seconds: float = DEFAULT_BATCH_SECONDS,
        timeout: float = DEFAULT_TIMEOUT,
        trace_limit: int = DEFAULT_TRACE_LIMIT,
        level: int = logging.NOTSET,
    ) -> None:
        super().__init__(level=level)
        self.token = token
        self.endpoint = endpoint
        self.batch_size = batch_size
        self.batch_seconds = batch_seconds
        self.timeout = timeout
        self.trace_limit = trace_limit

        self._hostname = socket.gethostname()
        self._queue: "queue.Queue[Any]" = queue.Queue()
        self._closed = False
        self._thread = threading.Thread(
            target=self._run, name="tailcove-sender", daemon=True
        )
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait((_LOG, self._normalize(record)))
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        """Sends whatever is buffered right now, regardless of size or age. Safe to call directly; blocks until the background thread confirms the flush."""
        self._signal(_FLUSH)

    def close(self) -> None:
        if self._closed:
            super().close()
            return

        self._closed = True
        self._signal(_CLOSE)
        self._thread.join(timeout=self.timeout + 1)
        super().close()

    def _signal(self, kind: str) -> None:
        if not self._thread.is_alive():
            return

        done = threading.Event()
        self._queue.put((kind, done))
        done.wait(timeout=self.timeout + 1)

    def _normalize(self, record: logging.LogRecord) -> Dict[str, Any]:
        context = extra_context(record)

        if record.exc_info:
            context["exception"] = format_exception(record.exc_info, self.trace_limit)

        return {
            "message": record.getMessage(),
            "level": normalize_level(record.levelname),
            "context": context,
            "host": self._hostname,
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
        }

    def _run(self) -> None:
        batch: List[Dict[str, Any]] = []
        deadline: Optional[float] = None

        while True:
            wait = None if deadline is None else max(0.0, deadline - time.monotonic())

            try:
                kind, payload = self._queue.get(timeout=wait)
            except queue.Empty:
                kind, payload = None, None

            if kind == _LOG:
                batch.append(payload)
                if deadline is None:
                    deadline = time.monotonic() + self.batch_seconds
            elif kind == _FLUSH:
                self._send(batch)
                batch, deadline = [], None
                payload.set()
                continue
            elif kind == _CLOSE:
                self._send(batch)
                payload.set()
                return

            if batch and (
                len(batch) >= self.batch_size
                or (deadline is not None and time.monotonic() >= deadline)
            ):
                self._send(batch)
                batch, deadline = [], None

    def _send(self, batch: List[Dict[str, Any]]) -> None:
        if not batch:
            return

        try:
            send_batch(self.endpoint, self.token, batch, self.timeout)
        except Exception as exc:
            print(f"[tailcove] failed to send log batch: {exc}", file=sys.stderr)
