<h1 align="center">tailcove</h1>

<p align="center">
  Send Python logs to <a href="https://tailcove.dev">Tailcove</a> with the standard <code>logging</code> module.<br>
  One handler, no dependencies, and it never slows down your code.
</p>

<p align="center">
  <a href="https://pypi.org/project/tailcove/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/tailcove?color=2DD4BF&labelColor=0A0A0A"></a>
  <a href="https://pypi.org/project/tailcove/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/tailcove?color=2DD4BF&labelColor=0A0A0A"></a>
  <a href="https://pypi.org/project/tailcove/"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/tailcove?color=2DD4BF&labelColor=0A0A0A"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-2DD4BF?labelColor=0A0A0A"></a>
</p>

<p align="center">
  <a href="https://tailcove.dev/docs/sending-logs/python">Documentation</a> ·
  <a href="https://github.com/tailcove/python/issues">Report a bug</a> ·
  <a href="https://app.tailcove.dev/register">Get started free</a>
</p>

---

## Why use it

- **Plain `logging`.** `TailcoveHandler` is a normal `logging.Handler`. Keep the loggers you already have.
- **Never blocks.** Records are batched and sent from a background thread, so a request or a hot loop never waits on the network.
- **No dependencies.** Delivery uses `urllib` from the standard library.
- **Safe.** A failed delivery is caught and never raised into your code.
- **Structured exceptions.** Log an exception and it arrives as data (class, message, location, trace), so identical errors group together.

## Install

```bash
pip install tailcove
```

Requires Python 3.9 or newer.

## Quick start

**1. Get a token.** Create a source in your [Tailcove dashboard](https://app.tailcove.dev) and copy its ingest token. It is shown only once, so save it somewhere safe (an environment variable is ideal).

**2. Add the handler.**

```python
import logging
import os

from tailcove import TailcoveHandler

logger = logging.getLogger("myapp")
logger.addHandler(TailcoveHandler(token=os.environ["TAILCOVE_TOKEN"]))
logger.setLevel(logging.INFO)

logger.info("user signed up", extra={"user_id": 42})
logger.error("payment failed", extra={"order_id": 99, "reason": "card_declined"})
```

**3. Open Tailcove.** Your records appear in search and live tail within a couple of seconds.

Buffered records are flushed when your program exits normally, because Python's own `logging.shutdown()` closes every handler.

## Options

| Argument | Default | What it does |
|---|---|---|
| `token` | — | Your source's ingest token. **Required.** |
| `endpoint` | `https://ingest.tailcove.dev/api/v1/logs` | The ingest URL. Only change this if you self-host. |
| `batch_size` | `50` | Send once this many records are buffered. |
| `batch_seconds` | `2.0` | Send once this many seconds have passed since the first buffered record. |
| `timeout` | `2.0` | Seconds a delivery attempt may take before giving up. |
| `trace_limit` | `10` | Most stack frames kept when a logged exception is rendered. |
| `level` | `logging.NOTSET` | Lowest level this handler processes, on top of the logger's own level. |

Records are sent once `batch_size` is reached or `batch_seconds` has passed, whichever comes first. They are never sent one HTTP request per log call. To send whatever is buffered right now, call `handler.flush()`. It blocks until the background thread confirms.

## Structured context

Anything you pass in `extra={...}` is shipped as the line's context, with the same keys:

```python
logger.info("order placed", extra={"order_id": 99, "total_cents": 4200})
```

## Exceptions

Log with `exc_info=True`, or use `logger.exception(...)` inside an `except` block, and the exception is sent as structured data and not as a flattened string:

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
    "trace": [
        "/app/billing/charge.py:42 in charge_card",
        "/app/orders/service.py:17 in place_order"
    ]
}
```

`location` is where the exception was raised, and `trace` is limited to `trace_limit` frames. It's the same shape the Laravel, Node and browser libraries use, so the same error groups into one issue whichever app reported it.

## Frameworks

### Django

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

### Flask

Attach the handler to the app logger, or to the root logger if you want every `logging.getLogger(__name__)` in the app to ship too:

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

## When delivery fails

Network errors and non-2xx responses never raise into your code. `emit()` follows the standard `Handler` convention and routes its own failures through `handleError()`. Errors on the background thread are caught and printed to stderr. Logging is best-effort by design.

## Help and feedback

- **Docs:** [tailcove.dev/docs/sending-logs/python](https://tailcove.dev/docs/sending-logs/python)
- **Bugs and feature requests:** [open an issue](https://github.com/tailcove/python/issues/new/choose)
- **Security problems:** please email **security@tailcove.dev** instead of opening a public issue.

## Other Tailcove libraries

[Laravel](https://github.com/tailcove/laravel) · [Node.js](https://github.com/tailcove/node) · [Browser](https://github.com/tailcove/browser)

## License

[MIT](LICENSE) © Akcybex
