from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from evidence.build import build_stub_pack

from correlator.db import connect, create_incident, upsert_signal, insert_candidates
from correlator.db import save_evidence_pack

from localiser.rank import rank_by_severity
from localiser.blame import rank_by_blame

@dataclass
class windowBuffer:
    window_sec : int = 90
    signals: list[dict] = field(default_factory=list)
    opened_at: datetime | None = None

    async def add(self, signal: dict) -> str | None:
        """Add signal; return incident_id if a window was flushed."""
        now = datetime.now(timezone.utc)
        if self.opened_at is None:
            self.opened_at = now
        self.signals.append(signal)

        conn = await connect()
        try:
            await upsert_signal(conn, signal)
            if (now - self.opened_at) >= timedelta(seconds=self.window_sec):
                return await self.flush(conn, now)
        finally:
            await conn.close()
        return None

    async def flush(self, conn=None, now: datetime | None = None) -> str | None:
        if not self.signals or self.opened_at is None:
            return None
        now = now or datetime.now(timezone.utc)
        owns_conn = conn is None
        if owns_conn:
            conn = await connect()
        try:
            incident_id = f"inc_{uuid.uuid4().hex[:12]}"
            ids = [s["signal_id"] for s in self.signals]
            await create_incident(conn, incident_id, self.opened_at, now, ids)

            edges = await conn.fetch(
                """
                SELECT src, dst, calls, call_share
                FROM edge_observation
                WHERE upper(bucket) > now() - interval '30 minutes'
                ORDER BY calls DESC
                LIMIT 200
                """
            )

            edge_dicts = [dict(r) for r in edges]
            cands = rank_by_blame(self.signals, edge_dicts) or rank_by_severity(self.signals)
            await insert_candidates(conn, incident_id, cands)

            pack = build_stub_pack(
                incident_id, self.opened_at, now, self.signals, cands
            )
            await save_evidence_pack(conn, incident_id, pack)

            print(
                f"correlator: incident={incident_id} signals={len(ids)} "
                f"method={(cands[0]['features'].get('method') if cands else None)}"
                f"nodes={sorted({s['node_id'] for s in self.signals})}",
                flush=True,
            )
            self.signals.clear()
            self.opened_at = None
            return incident_id
        finally:
            if owns_conn and conn is not None:
                await conn.close()