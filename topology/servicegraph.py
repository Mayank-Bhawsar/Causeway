from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

VM_URL = os.getenv("VM_URL", "http://victoria-metrics:8428")

QUERY = 'sum by (client, server) (increase(traces_service_graph_request_total[2m]))'


async def fetch_edges() -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{VM_URL}/api/v1/query", params={"query": QUERY})
        r.raise_for_status()
        edges: list[dict] = []
        for row in r.json().get("data", {}).get("result", []):
            m = row["metric"]
            client_svc = m.get("client")
            server_svc = m.get("server")
            if not client_svc or not server_svc:
                continue
            calls = float(row["value"][1])
            if calls <=0:
                continue
            edges.append({
                "src": f"svc:{client_svc}",
                "dst": f"svc:{server_svc}",
                "rel": "CALLS",
                "calls": int(calls),
            })
        return edges