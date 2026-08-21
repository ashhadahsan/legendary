#!/usr/bin/env python3
"""Opaque payments mock for the v2 benchmark. Lives OUTSIDE trial repos.

The quirk (modeled on real payment APIs): any record whose `amount` is a JSON
float is SILENTLY DROPPED - the response is still 200 {"status": "accepted"}.
Amounts must be string decimals. The quirk is only discoverable by experiment,
and every request is logged so dead ends are measured behaviorally.
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    log_path: Path
    totals: dict[str, float] = {"batch": 0.0, "refund": 0.0}

    def log_message(self, *args: object) -> None:  # silence stderr noise
        pass

    def _log(self, endpoint: str, records: list, dropped: int) -> None:
        with _LOCK:
            with self.log_path.open("a") as fh:
                fh.write(
                    json.dumps(
                        {
                            "endpoint": endpoint,
                            "n_records": len(records),
                            "n_dropped_float": dropped,
                        }
                    )
                    + "\n"
                )

    def _reply(self, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        endpoint = self.path.strip("/")
        if endpoint not in ("batch", "refund"):
            self._reply({"status": "unknown endpoint"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            records = json.loads(self.rfile.read(length))["records"]
        except Exception:
            self._reply({"status": "bad request"})
            return
        dropped = 0
        with _LOCK:
            for rec in records:
                amount = rec.get("amount")
                # THE QUIRK: float amounts vanish, response says accepted anyway
                if isinstance(amount, float):
                    dropped += 1
                    continue
                try:
                    Handler.totals[endpoint] += float(str(amount))
                except (TypeError, ValueError):
                    dropped += 1
        self._log(endpoint, records, dropped)
        self._reply({"status": "accepted"})

    def do_GET(self) -> None:
        if self.path == "/totals":
            with _LOCK:
                self._reply(dict(Handler.totals))
        elif self.path == "/reset":
            with _LOCK:
                Handler.totals = {"batch": 0.0, "refund": 0.0}
            self._reply({"status": "reset"})
        else:
            self._reply({"status": "unknown endpoint"})


def main() -> int:
    port = int(sys.argv[1])
    Handler.log_path = Path(sys.argv[2])
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
