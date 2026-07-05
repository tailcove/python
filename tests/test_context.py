from __future__ import annotations

import logging

from tailcove.context import extra_context

from helpers import make_record


def test_extra_context_keeps_only_caller_supplied_keys():
    record = make_record(message="hi", extra={"user_id": 42, "order_id": 7})

    assert extra_context(record) == {"user_id": 42, "order_id": 7}


def test_extra_context_is_empty_when_no_extra_was_passed():
    record = make_record(message="hi")

    assert extra_context(record) == {}


def test_extra_context_never_leaks_standard_record_attributes():
    record = make_record(message="hi", extra={"custom": "value"})

    context = extra_context(record)

    assert "custom" in context
    for standard_attr in ("msg", "levelname", "levelno", "pathname", "lineno", "funcName", "process", "thread"):
        assert standard_attr not in context
