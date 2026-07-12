from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


def llm_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def get_model() -> str:
    return os.getenv("LLM_MODEL", "gpt-4o-mini")


def analyze_with_llm(
    *,
    text: str,
    star_rating: float | None,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    client = OpenAI()
    response = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
