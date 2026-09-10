"""Docker healthcheck: GET local worker /healthz."""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    url = os.getenv("WORKER_HEALTH_URL", "http://127.0.0.1:8085/healthz")
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            if resp.status != 200:
                print(f"worker health bad status={resp.status}", file=sys.stderr)
                return 1
    except urllib.error.HTTPError as exc:
        print(f"worker health http error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"worker health unreachable: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
