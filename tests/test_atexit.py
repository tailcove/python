from __future__ import annotations

import subprocess
import sys
import textwrap


def test_flushes_pending_records_at_normal_interpreter_exit(server):
    """
    No explicit flush()/close() call — relies entirely on the stdlib's own
    atexit hook (logging.shutdown(), registered by the logging module for
    every Handler subclass) to drain the queue when the process exits
    normally. Run in a real subprocess against the real capturing server so
    this exercises the actual exit path rather than trusting it by
    inspection.
    """
    script = textwrap.dedent(
        f"""
        import logging
        from tailcove import TailcoveHandler

        logger = logging.getLogger("atexit-test")
        logger.setLevel(logging.INFO)
        logger.addHandler(TailcoveHandler(
            token="t",
            endpoint={server.endpoint!r},
            batch_size=50,
            batch_seconds=100,
        ))
        logger.info("flushed on exit")
        """
    )

    result = subprocess.run([sys.executable, "-c", script], timeout=10)

    assert result.returncode == 0
    assert len(server.requests) == 1
    assert server.lines()[0]["message"] == "flushed on exit"
