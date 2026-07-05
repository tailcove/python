from __future__ import annotations

import logging

from tailcove import TailcoveHandler

from helpers import make_record


def test_flush_does_not_raise_when_the_endpoint_is_unreachable(dead_endpoint):
    handler = TailcoveHandler(token="t", endpoint=dead_endpoint, timeout=0.5)

    handler.emit(make_record(message="will fail to send"))
    handler.flush()  # must not raise even though delivery failed

    handler.close()


def test_flush_does_not_raise_when_the_endpoint_responds_with_a_non_2xx_status(server):
    server.respond_with(500)

    handler = TailcoveHandler(token="t", endpoint=server.endpoint, timeout=1.0)
    handler.emit(make_record(message="server hiccup"))
    handler.flush()  # must not raise even though the server rejected the batch

    handler.close()


def test_flush_does_not_raise_when_context_contains_a_circular_reference(server):
    circular: dict = {}
    circular["self"] = circular

    handler = TailcoveHandler(token="t", endpoint=server.endpoint)
    handler.emit(make_record(message="circular context", extra={"payload": circular}))
    handler.flush()  # json.dumps fails on the circular ref; must not raise or hang

    handler.close()


def test_emit_never_raises_even_with_a_malformed_format_string():
    logging.raiseExceptions = False
    try:
        handler = TailcoveHandler(token="t", endpoint="http://127.0.0.1:1/api/v1/logs")
        # A %d placeholder fed a non-numeric arg: getMessage() raises
        # TypeError inside _normalize(), which emit() must catch.
        record = logging.getLogger("tailcove-tests").makeRecord(
            "tailcove-tests", logging.ERROR, __file__, 0, "value: %d", ("not a number",), None
        )

        handler.emit(record)  # must not raise
        handler.close()
    finally:
        logging.raiseExceptions = True
