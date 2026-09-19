"""Export agent transcript JSONL to full_chat.md (user + assistant text only)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT = Path(
    r"C:\Users\Mayank.Bhawsar\.cursor\projects"
    r"\c-Users-Mayank-Bhawsar-OneDrive-Heuristics-Informatics-Pvt-Ltd-Desktop-test2-Projects-AIOps-Causeway"
    r"\agent-transcripts\a71e8900-d399-41e9-a13a-7c0de17cbd6a"
    r"\a71e8900-d399-41e9-a13a-7c0de17cbd6a.jsonl"
)
OUT = ROOT / "full_chat.md"


def main() -> None:
    lines: list[str] = [
        "# Causeway — Full Chat Transcript",
        "",
        f"> Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "> Source: `agent-transcripts/a71e8900-d399-41e9-a13a-7c0de17cbd6a.jsonl`",
        "> User and assistant **text** messages in chronological order.",
        "> Tool calls / tool results omitted. Turns stored as `[REDACTED]` only are noted.",
        "",
    ]
    n = 0
    with TRANSCRIPT.open(encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            role = ev.get("role")
            if role not in ("user", "assistant"):
                continue
            msg = ev.get("message") or {}
            content = msg.get("content")
            if not content:
                continue
            texts: list[str] = []
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        texts.append(part.get("text", ""))
            body = "\n\n".join(t for t in texts if t).strip()
            if not body:
                continue
            if body.strip() == "[REDACTED]":
                body = "*(Assistant turn — full text omitted in transcript export.)*"
            n += 1
            title = "User" if role == "user" else "Assistant"
            lines.extend([f"## {n}. {title}", "", body, "", "---", ""])
    lines.append(f"*End of transcript — {n} messages.*")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} ({n} messages, {OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
