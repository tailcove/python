from __future__ import annotations

import logging
import sys
import traceback

from tailcove import TailcoveHandler
from tailcove.exceptions import format_exception


def test_renders_class_message_location_and_a_trimmed_trace():
    try:
        raise RuntimeError("something broke")
    except RuntimeError:
        exc_info = sys.exc_info()
        formatted = format_exception(exc_info, trace_limit=10)
        expected_frame = traceback.extract_tb(exc_info[2])[-1]

    assert formatted["class"] == "RuntimeError"
    assert formatted["message"] == "something broke"
    assert formatted["location"] == f"{expected_frame.filename}:{expected_frame.lineno}"
    assert isinstance(formatted["trace"], list)
    assert all(isinstance(frame, str) for frame in formatted["trace"])


def test_qualifies_non_builtin_exception_classes_with_their_module():
    class CardDeclined(Exception):
        pass

    try:
        raise CardDeclined("insufficient funds")
    except CardDeclined:
        formatted = format_exception(sys.exc_info())

    assert formatted["class"] == f"{__name__}.{CardDeclined.__qualname__}"
    assert formatted["message"] == "insufficient funds"


def test_trims_the_trace_to_the_configured_limit():
    def inner():
        raise RuntimeError("deep")

    def outer():
        inner()

    try:
        outer()
    except RuntimeError:
        formatted = format_exception(sys.exc_info(), trace_limit=1)

    assert len(formatted["trace"]) == 1


def test_handles_no_traceback_gracefully():
    formatted = format_exception((RuntimeError, RuntimeError("no traceback"), None))

    assert formatted["class"] == "RuntimeError"
    assert formatted["message"] == "no traceback"
    assert formatted["location"] == ""
    assert formatted["trace"] == []


def test_handler_ships_exc_info_under_context_exception_matching_laravel_shape(server):
    handler = TailcoveHandler(token="t", endpoint=server.endpoint, trace_limit=5)
    logger = logging.getLogger("tailcove-exception-test")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        raise ValueError("bad input")
    except ValueError:
        logger.exception("request failed")

    handler.flush()

    exception = server.lines()[0]["context"]["exception"]
    assert set(exception.keys()) == {"class", "message", "location", "trace"}
    assert exception["class"] == "ValueError"
    assert exception["message"] == "bad input"
    assert exception["location"].startswith(__file__ + ":")
    assert len(exception["trace"]) <= 5

    logger.removeHandler(handler)
    handler.close()
