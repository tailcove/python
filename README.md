<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/tailcove/.github/main/profile/assets/packages/python-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/tailcove/.github/main/profile/assets/packages/python-light.svg">
  <img alt="tailcove: Tailcove for Python" src="https://raw.githubusercontent.com/tailcove/.github/main/profile/assets/packages/python-dark.svg" width="100%">
</picture>

<p align="center">
  <a href="https://tailcove.dev/docs/sending-logs/python"><img alt="Documentation" src="https://img.shields.io/badge/Documentation-2DD4BF?style=for-the-badge&logoColor=0A0A0A"></a>
  <a href="https://app.tailcove.dev/register"><img alt="Get started free" src="https://img.shields.io/badge/Get%20started%20free-0A0A0A?style=for-the-badge"></a>
  <a href="https://github.com/tailcove/python/issues/new/choose"><img alt="Report a bug" src="https://img.shields.io/badge/Report%20a%20bug-0A0A0A?style=for-the-badge"></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/tailcove/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/tailcove?color=2DD4BF&labelColor=0A0A0A"></a>
  <a href="https://pypi.org/project/tailcove/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/tailcove?color=2DD4BF&labelColor=0A0A0A"></a>
  <a href="https://pypi.org/project/tailcove/"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/tailcove?color=2DD4BF&labelColor=0A0A0A"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-2DD4BF?labelColor=0A0A0A"></a>
</p>

<br>

<h3 align="center">Send Python logs to Tailcove with the standard logging module.</h3>

<br>

<table>
  <tr>
    <td width="33%" valign="top">
      <h4>🐍 &nbsp;Plain <code>logging</code></h4>
      <code>TailcoveHandler</code> is a normal <code>logging.Handler</code>. Keep the loggers you have.
    </td>
    <td width="33%" valign="top">
      <h4>🧵 &nbsp;Never blocks</h4>
      Records are batched and sent from a background thread, so nothing waits on the network.
    </td>
    <td width="33%" valign="top">
      <h4>📦 &nbsp;No dependencies</h4>
      Delivery uses <code>urllib</code> from the standard library.
    </td>
  </tr>
  <tr>
    <td width="33%" valign="top">
      <h4>🛡️ &nbsp;Safe</h4>
      A failed delivery is caught and never raised into your code.
    </td>
    <td width="33%" valign="top">
      <h4>🧩 &nbsp;Structured exceptions</h4>
      Class, message, location and trace arrive as data, so identical errors group together.
    </td>
    <td width="33%" valign="top">
      <h4>🌐 &nbsp;Django &amp; Flask</h4>
      Copy-paste setup for both, below.
    </td>
  </tr>
</table>

<br>

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

[MIT](LICENSE) © AKCybex

<br>

<p align="center">
  <sub>Built by <a href="https://akcybex.com">AKCybex</a> &nbsp;·&nbsp; <a href="https://tailcove.dev">tailcove.dev</a></sub>
</p>
