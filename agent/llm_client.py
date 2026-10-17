"""Gemini-backed proposal client for the AFTERMATH agent.

Reads GEMINI_API_KEY from the environment (never from a committed file).
Raises AgentUnavailable when the key or SDK is missing, or when the API call
fails, so callers can fall back cleanly instead of crashing.
"""
from __future__ import annotations

import os

from .prompts import SYSTEM_PROMPT
from .schemas import ProposedAction

# Tried in order; override with GEMINI_MODEL="model-a,model-b".
DEFAULT_MODELS = ("gemini-2.5-flash", "gemini-2.0-flash")


class AgentUnavailable(RuntimeError):
    """The LLM path is not usable (missing key/SDK or API failure)."""


def gemini_propose(*, ticket: str, customer_id: str, refund_limit: float) -> ProposedAction:
    """Ask Gemini for a structured ProposedAction for the given ticket."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise AgentUnavailable("GEMINI_API_KEY is not set")
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise AgentUnavailable("google-genai package is not installed") from exc

    models = [m.strip() for m in os.getenv("GEMINI_MODEL", "").split(",") if m.strip()]
    if not models:
        models = list(DEFAULT_MODELS)

    user_prompt = (
        f"Support ticket:\n{ticket}\n\n"
        f"Customer ID: {customer_id}\n"
        f"Refund limit (major currency units): {refund_limit:g}\n\n"
        "Propose the structured action the customer is requesting."
    )

    client = genai.Client(api_key=api_key)
    last_error: Exception | None = None
    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ProposedAction,
                    temperature=0,
                ),
            )
            return ProposedAction.model_validate_json(response.text)
        except Exception as exc:  # try the next model, then give up honestly
            last_error = exc
    raise AgentUnavailable(f"Gemini proposal failed: {last_error}")
