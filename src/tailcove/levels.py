from __future__ import annotations

#: Syslog-style levels, matching the set the ingest endpoint normalizes to
#: (see the log-ingestion skill). Standard library level names map onto
#: these directly; anything unrecognized (including a custom level name the
#: server has never heard of) falls back to "info", same as the server.
_LEVEL_MAP = {
    "DEBUG": "debug",
    "INFO": "info",
    "NOTICE": "notice",
    "WARNING": "warning",
    "WARN": "warning",
    "ERROR": "error",
    "CRITICAL": "critical",
    "FATAL": "critical",
    "ALERT": "alert",
    "EMERGENCY": "emergency",
}


def normalize_level(levelname: str) -> str:
    return _LEVEL_MAP.get(levelname.upper(), "info")
