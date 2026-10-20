# tailcove (Python)

`TailcoveHandler` is a standard-library `logging.Handler` for shipping
application logs to [Tailcove](https://tailcove.dev). Batches up to 50
records (or 2 seconds, whichever comes first) and ships them as NDJSON from
a background thread, so logging never adds latency to a request or a hot
loop.

Zero required dependencies — delivery uses `urllib` from the standard
library.

A delivery failure never raises into your application. `emit()` follows
the stdlib `Handler` convention of catching its own failures and routing
them through `self.handleError()`; failures on the background thread are
caught and printed to stderr, never propagated.

## Install

```bash
pip install tailcove
```

```python
import logging
from tailcove import TailcoveHandler

logger = logging.getLogger("myapp")
logger.addHandler(TailcoveHandler(token="your-source-ingest-token"))
logger.setLevel(logging.INFO)

logger.info("user signed up", extra={"user_id": 42})
logger.error("payment failed", extra={"order_id": 99, "reason": "card_declined"})
```

That's it — every record now ships to your Tailcove source. Flushing at
interpreter exit is automatic: every `logging.Handler` is flushed and
closed by the stdlib's own `logging.shutdown()` atexit hook, so buffered
lines aren't lost when the process exits normally.

## Configuration reference

| Argument | Default | Purpose |
|---|---|---|
| `token` | — | The source's ingest token. Required. |
| `endpoint` | `https://ingest.tailcove.dev/api/v1/logs` | Your source's ingest URL. |
| `batch_size` | `50` | Flush once this many records are buffered. |
| `batch_seconds` | `2.0` | Flush once this many seconds have passed since the first buffered record. |
| `timeout` | `2.0` | Seconds before a delivery attempt gives up. |
| `trace_limit` | `10` | Max stack frames kept when rendering a logged exception. |
| `level` | `logging.NOTSET` | Minimum level this handler processes (in addition to the logger's own level). |

## How batching works

Records are buffered in memory on a background thread and flushed as one
batch once either threshold is hit — **never** one HTTP request per log
call:

- `batch_size` (default `50`) — flush once this many records are buffered.
- `batch_seconds` (default `2.0`) — flush once this many seconds have
  passed since the first buffered record, whichever comes first.

Call `handler.flush()` to send whatever's buffered immediately, regardless
of either threshold — it blocks until the background thread confirms the
flush.

## Structured context

Anything passed via `extra={...}` lands directly in the shipped line's
`context`, keyed exactly as given:

```python
logger.info("order placed", extra={"order_id": 99, "total_cents": 4200})
```

## Exceptions

Log with `exc_info=True` (or pass an exception via `logger.exception(...)`
inside an `except` block) and it's rendered as structured data under
`context["exception"]` instead of a flattened string — the same
`{class, message, location, trace}` shape the `tailcove/laravel` package
uses, so fingerprinting groups the same underlying error the same way
regardless of which client reported it:

```python
try:
    charge_card(order)
except CardDeclined:
    logger.error("payment failed", exc_info=True)
```

```json
"exception": {
    "class": "billing.errors.CardDeclined",
    "message": "insufficient funds",
    "location": "/app/billing/charge.py:42",
    "trace": ["/app/billing/charge.py:42 in charge_card", "/app/orders/service.py:17 in place_order"]
}
```

`location` is the file:line where the exception was actually raised (the
innermost frame); `trace` is trimmed to `trace_limit` frames the same way
the Laravel package trims its stringified trace.

## Django

Add the handler to `LOGGING` in `settings.py`:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "tailcove": {
            "class": "tailcove.TailcoveHandler",
            "token": env("TAILCOVE_TOKEN"),
        },
    },
    "root": {
        "handlers": ["console", "tailcove"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["tailcove"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}
```

## Flask

Attach it to Flask's app logger (or the root logger, if you want every
`logging.getLogger(__name__)` call across the app to ship too):

```python
from flask import Flask
from tailcove import TailcoveHandler

app = Flask(__name__)
app.logger.addHandler(TailcoveHandler(token=app.config["TAILCOVE_TOKEN"]))
app.logger.setLevel("INFO")


@app.errorhandler(Exception)
def handle_exception(exc):
    app.logger.error("unhandled exception", exc_info=exc)
    raise
```

## Failure handling

A delivery failure — a network error or a non-2xx response — never raises
into your application. It's caught on the background thread and printed to
stderr. Logging is best-effort by design; it should never be the reason
your app crashes.
