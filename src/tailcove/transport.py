from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List


class DeliveryError(Exception):
    """Raised when a batch fails to reach the ingest endpoint (network error or non-2xx response)."""


def send_batch(
    endpoint: str,
    token: str,
    batch: List[Dict[str, Any]],
    timeout: float,
) -> None:
    """
    Ships a batch as NDJSON — one JSON object per line, per the ingest
    endpoint's payload sniffing (see the log-ingestion skill). Uses only
    `urllib` from the standard library so the package has zero required
    dependencies. Raises DeliveryError on a network failure or non-2xx
    response; callers decide whether that's swallowed or surfaced.
    """
    body = "\n".join(json.dumps(line, default=str) for line in batch).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-ndjson",
            "Authorization": f"Bearer {token}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        raise DeliveryError(
            f"tailcove: ingest endpoint responded with status {exc.code}"
        ) from exc
    except urllib.error.URLError as exc:
        raise DeliveryError(
            f"tailcove: request to ingest endpoint failed ({exc.reason})"
        ) from exc

    if status >= 300:
        raise DeliveryError(f"tailcove: ingest endpoint responded with status {status}")
