from __future__ import annotations

import json
import os

from openai import AsyncOpenAI

SYSTEM = """You are Causeway's incident narrator.
You receive ONLY an evidence pack JSON. Return valid JSON with keys:
summary, ranked_causes (list of {node_id, why, evidence_refs}),
claims (list of {text, evidence_refs}), uncertainty.
Use top_cause from the pack as the primary ranked cause when present.
Every evidence_refs entry MUST be an exact "key" from pack entries (e.g. EV-SIG-0001).
Do not invent numbers; copy values verbatim from cited evidence entries."""


async def narrate(
    pack: dict | str,
    validation_errors: list[str] | None = None,
) -> dict:
    if isinstance(pack, str):
        pack = json.loads(pack)
    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        timeout=60.0,
    )
    user_content = json.dumps(pack)
    if validation_errors:
        user_content += (
            "\n\nPrevious response failed validation. Fix and return JSON only:\n"
            + json.dumps(validation_errors)
        )
    resp = await client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_content},
        ],
    )
    content = resp.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned empty content")
    return json.loads(content)
