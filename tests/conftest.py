from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List

import pytest


class _CapturingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming convention)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.server.requests.append(  # type: ignore[attr-defined]
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": body.decode("utf-8"),
            }
        )
        self.send_response(self.server.response_status)  # type: ignore[attr-defined]
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass  # keep test output quiet


class CapturingServer:
    """
    A real local HTTP server standing in for the ingest endpoint — good
    enough to capture the exact request TailcoveHandler sends without
    mocking urllib, mirroring the tailcove/laravel test suite's raw-socket
    approach.
    """

    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _CapturingHandler)
        self._server.requests = []  # type: ignore[attr-defined]
        self._server.response_status = 202  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def respond_with(self, status: int) -> None:
        """Makes every subsequent request to this server receive `status` instead of 202."""
        self._server.response_status = status  # type: ignore[attr-defined]

    @property
    def endpoint(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/api/v1/logs"

    @property
    def requests(self) -> List[Dict[str, Any]]:
        return self._server.requests  # type: ignore[attr-defined]

    def lines(self, call_index: int = 0) -> List[Dict[str, Any]]:
        body = self.requests[call_index]["body"]
        return [json.loads(line) for line in body.splitlines() if line]

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


@pytest.fixture
def server():
    srv = CapturingServer()
    yield srv
    srv.shutdown()


@pytest.fixture
def dead_endpoint() -> str:
    """An address nothing is listening on, for exercising delivery failures without a flaky external host."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    return f"http://127.0.0.1:{port}/api/v1/logs"


def wait_until(predicate, timeout: float = 2.0, interval: float = 0.01) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)

    return predicate()
