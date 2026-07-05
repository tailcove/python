from __future__ import annotations

import logging
import time

from tailcove import TailcoveHandler

from conftest import wait_until
from helpers import make_record


def test_flushes_once_batch_size_is_reached(server):
    handler = TailcoveHandler(
        token="test-token", endpoint=server.endpoint, batch_size=2, batch_seconds=100
    )

    handler.emit(make_record(message="first"))
    handler.emit(make_record(message="second"))
    handler.flush()  # synchronizes with the background thread; a no-op if size already flushed

    assert len(server.requests) == 1
    lines = server.lines()
    assert [line["message"] for line in lines] == ["first", "second"]

    handler.close()


def test_flushes_after_batch_seconds_even_if_batch_size_never_reached(server):
    handler = TailcoveHandler(
        token="test-token", endpoint=server.endpoint, batch_size=50, batch_seconds=0.05
    )

    handler.emit(make_record(message="lonely line"))

    assert wait_until(lambda: len(server.requests) == 1, timeout=2)
    assert server.lines()[0]["message"] == "lonely line"

    handler.close()


def test_does_not_send_while_under_both_thresholds(server):
    handler = TailcoveHandler(
        token="test-token", endpoint=server.endpoint, batch_size=50, batch_seconds=100
    )

    handler.emit(make_record(message="not yet"))
    time.sleep(0.1)

    assert server.requests == []

    handler.close()


def test_flush_sends_immediately_regardless_of_thresholds(server):
    handler = TailcoveHandler(
        token="test-token", endpoint=server.endpoint, batch_size=50, batch_seconds=100
    )

    handler.emit(make_record(message="first"))
    handler.flush()

    assert len(server.requests) == 1

    handler.close()


def test_flush_is_a_noop_when_nothing_is_buffered(server):
    handler = TailcoveHandler(token="test-token", endpoint=server.endpoint)

    handler.flush()

    assert server.requests == []

    handler.close()


def test_sends_the_token_as_a_bearer_header_and_the_body_as_ndjson(server):
    handler = TailcoveHandler(token="secret-token", endpoint=server.endpoint)

    handler.emit(make_record(message="boom", level=logging.ERROR, extra={"order_id": 42}))
    handler.flush()

    request = server.requests[0]
    assert request["headers"]["Authorization"] == "Bearer secret-token"
    assert request["headers"]["Content-Type"] == "application/x-ndjson"

    line = server.lines()[0]
    assert line["message"] == "boom"
    assert line["level"] == "error"
    assert line["context"]["order_id"] == 42
    assert isinstance(line["host"], str) and line["host"]
    assert isinstance(line["ts"], str) and line["ts"]

    handler.close()


def test_normalizes_a_record_into_the_ingest_payload_shape(server):
    handler = TailcoveHandler(token="tok", endpoint=server.endpoint, batch_size=1)

    handler.emit(make_record(message="boom", extra={"user_id": 42}))
    handler.flush()

    line = server.lines()[0]
    assert line["message"] == "boom"
    assert line["level"] == "error"
    assert line["context"] == {"user_id": 42}
    assert "host" in line
    assert "ts" in line

    handler.close()


def test_normalizes_an_unrecognized_level_name_to_info():
    from tailcove.levels import normalize_level

    assert normalize_level("TRACE") == "info"
    assert normalize_level("debug") == "debug"
    assert normalize_level("WARNING") == "warning"


def test_does_nothing_when_disabled_via_high_level_threshold(server):
    handler = TailcoveHandler(token="t", endpoint=server.endpoint, level=logging.CRITICAL)
    logger = logging.getLogger("tailcove-disabled-test")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.info("should be dropped")
    handler.flush()

    assert server.requests == []

    logger.removeHandler(handler)
    handler.close()
