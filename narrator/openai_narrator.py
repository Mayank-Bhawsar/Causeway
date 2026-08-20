from __future__ import annotations

import json 
import os

from openai import AsyncOpenAI

SYSTEM = """ You are Causeway's incident narrator.
You receive ONLY an evidence pack JSON. Return valid JSON with summary,
ranked_causes (list of {node_id , why, evidence_refs}),
claims (list of {text, evidence_refs}), uncertainty.
Every evidence_refs entry MUST exist in the pack entries' "key" field.
Do Not invent numbers not present in the pack."""


async def narrate(pack: dict) -> dict:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = await client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        response_format={"type" : "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(pack)},
        ],
    )
    return json.loads(resp.choices[0].message.content)