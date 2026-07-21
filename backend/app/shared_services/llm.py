from __future__ import annotations

import json
import logging
import os
from typing import Any, Literal, Optional, Type

import instructor
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

Provider = Literal["ollama", "openai", "gemini"]

DEFAULT_MODELS = {
    "ollama": "llama3.2",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
}


def get_provider() -> Provider:
    value = (os.getenv("LLM_PROVIDER") or "ollama").strip().lower()
    if value not in DEFAULT_MODELS:
        raise ValueError(f"Unknown LLM_PROVIDER={value!r}. Use ollama|openai|gemini.")
    return value  # type: ignore[return-value]


def llm_enabled() -> bool:
    provider = get_provider()
    if provider == "ollama":
        return True
    if provider == "openai":
        return bool((os.getenv("OPENAI_API_KEY") or "").strip())
    return bool((os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip())


def get_model() -> str:
    provider = get_provider()
    if provider == "ollama":
        return (os.getenv("OLLAMA_MODEL") or os.getenv("LLM_MODEL") or DEFAULT_MODELS["ollama"]).strip()
    if provider == "openai":
        return (os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or DEFAULT_MODELS["openai"]).strip()
    return (os.getenv("LLM_MODEL") or os.getenv("GEMINI_MODEL") or DEFAULT_MODELS["gemini"]).strip()


def _to_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, BaseModel):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        return json.loads(result or "{}")
    raise TypeError(f"Unexpected LLM result type: {type(result)}")


def _call_ollama(
    *,
    messages: list[dict[str, str]],
    model: str,
    response_format: Type[BaseModel] | None,
    temperature: float,
    mode: instructor.Mode,
) -> dict[str, Any]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    if response_format is not None:
        client = instructor.from_provider(
            f"ollama/{model}",
            base_url=base_url,
            mode=mode,
        )
        return _to_dict(
            client.create(
                messages=messages,
                temperature=temperature,
                response_model=response_format,
                max_retries=3,
            )
        )

    client = OpenAI(base_url=base_url, api_key="ollama")
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return json.loads(completion.choices[0].message.content or "{}")


def _call_openai(
    *,
    messages: list[dict[str, str]],
    model: str,
    response_format: Type[BaseModel] | None,
    temperature: float,
) -> dict[str, Any]:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if response_format is not None:
        client = instructor.from_openai(OpenAI(api_key=api_key), mode=instructor.Mode.JSON)
        return _to_dict(
            client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_model=response_format,
                max_retries=3,
            )
        )

    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return json.loads(completion.choices[0].message.content or "{}")


def _call_gemini(
    *,
    messages: list[dict[str, str]],
    model: str,
    response_format: Type[BaseModel] | None,
    temperature: float,
) -> dict[str, Any]:
    # instructor reads GOOGLE_API_KEY; accept GEMINI_API_KEY as alias.
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

    if response_format is not None:
        client = instructor.from_provider(f"google/{model}")
        return _to_dict(
            client.create(
                messages=messages,
                temperature=temperature,
                response_model=response_format,
                max_retries=3,
            )
        )

    from google import genai

    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    prompt = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    prompt += "\n\nRespond with a single JSON object only."
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": temperature},
    )
    return json.loads(response.text or "{}")


def analyze_with_llm(
    *,
    text: str,
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    response_format: Optional[Type[BaseModel]] = None,
    temperature: float = 0.3,
    mode: instructor.Mode = instructor.Mode.JSON,
) -> dict[str, Any]:
    """Call Ollama, OpenAI, or Gemini based on LLM_PROVIDER. Always returns a dict."""
    _ = text
    provider = get_provider()
    resolved_model = (model or "").strip() or get_model()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        if provider == "ollama":
            return _call_ollama(
                messages=messages,
                model=resolved_model,
                response_format=response_format,
                temperature=temperature,
                mode=mode,
            )
        if provider == "openai":
            return _call_openai(
                messages=messages,
                model=resolved_model,
                response_format=response_format,
                temperature=temperature,
            )
        return _call_gemini(
            messages=messages,
            model=resolved_model,
            response_format=response_format,
            temperature=temperature,
        )
    except Exception as e:
        logger.error("Error in %s API call: %s", provider, e)
        raise
