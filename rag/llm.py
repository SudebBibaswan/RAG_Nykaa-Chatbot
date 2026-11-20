"""Provider-neutral LLM layer. OpenAI is the default; Claude stays available.

Select with LLM_PROVIDER=openai|anthropic (defaults to whichever key is set, OpenAI first).
Everything else in the pipeline calls only these functions.
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Iterator, TypeVar

from pydantic import BaseModel

from . import config

T = TypeVar("T", bound=BaseModel)


class Refusal(RuntimeError):
    """The model declined to answer."""


# ------------------------------------------------------------------ circuit breaker
# Quota and auth errors won't fix themselves within a conversation. After one, skip the
# LLM for a while so the app answers instantly in retrieval-only mode instead of every
# question waiting through retries.
_PAUSE_SECONDS = 600
_paused_until = 0.0
_pause_reason = ""


def is_account_problem(e: Exception) -> bool:
    text = f"{type(e).__name__} {e}".lower()
    return any(k in text for k in ("insufficient_quota", "no credits", "billing", "authentication", "invalid_api_key", "incorrect api key", "permission"))


def friendly(e: Exception | str) -> str:
    """Turn a provider error into one plain sentence for the UI."""
    t = str(e).lower()
    name = {"openai": "OpenAI", "anthropic": "Anthropic"}.get(config.LLM_PROVIDER, config.LLM_PROVIDER)
    if "credit" in t or "quota" in t or "billing" in t:
        return f"The {name} account is out of credits"
    if "auth" in t or "api key" in t or "api_key" in t:
        return f"The {name} API key was rejected"
    if "rate" in t:
        return f"{name} is rate-limiting requests"
    return f"{name} is unreachable"


def pause(reason: str) -> None:
    global _paused_until, _pause_reason
    _paused_until = time.time() + _PAUSE_SECONDS
    _pause_reason = reason


def available() -> tuple[bool, str]:
    """Whether generation can be attempted now, and if not, why."""
    if not config.has_llm():
        return False, "no API key"
    if time.time() < _paused_until:
        return False, _pause_reason
    return True, ""


# ------------------------------------------------------------------ clients
@lru_cache(maxsize=1)
def openai_client():
    from openai import OpenAI

    return OpenAI(timeout=60.0, max_retries=2)


@lru_cache(maxsize=1)
def anthropic_client():
    import anthropic

    return anthropic.Anthropic(timeout=60.0, max_retries=2)


ANTHROPIC_FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _openai_effort(effort: str) -> dict:
    return {"reasoning_effort": effort} if effort else {}


# ------------------------------------------------------------------ structured output
def structured(system: str, user: str, schema: type[T], model: str, effort: str = "") -> T | None:
    """One call that must return an instance of `schema`, or None if the model declined."""
    if config.LLM_PROVIDER == "openai":
        r = openai_client().chat.completions.parse(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format=schema,
            **_openai_effort(effort),
        )
        msg = r.choices[0].message
        return None if msg.refusal else msg.parsed

    resp = anthropic_client().beta.messages.parse(
        model=model,
        max_tokens=4000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_format=schema,
        output_config={"effort": effort or "low"},
        betas=[ANTHROPIC_FALLBACK_BETA],
        fallbacks="default",
    )
    return None if resp.stop_reason == "refusal" else resp.parsed_output


# ------------------------------------------------------------------ streamed text
def stream(system: str, messages: list[dict], model: str, effort: str, max_tokens: int) -> Iterator[str]:
    """Yields text deltas. Raises Refusal if the model declines."""
    if config.LLM_PROVIDER == "openai":
        chunks = openai_client().chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, *messages],
            stream=True,
            max_completion_tokens=max_tokens,
            **_openai_effort(effort),
        )
        for chunk in chunks:
            if not chunk.choices:
                continue
            ch = chunk.choices[0]
            if getattr(ch.delta, "refusal", None):
                raise Refusal(ch.delta.refusal)
            if ch.delta.content:
                yield ch.delta.content
            if ch.finish_reason == "content_filter":
                raise Refusal("content filter")
        return

    with anthropic_client().beta.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
        output_config={"effort": effort or "low"},
        betas=[ANTHROPIC_FALLBACK_BETA],
        fallbacks="default",
    ) as s:
        yield from s.text_stream
        final = s.get_final_message()
    if final.stop_reason == "refusal":
        raise Refusal("refusal")


# ------------------------------------------------------------------ voice (OpenAI)
def voice_available() -> bool:
    return config.has_openai()


def speech(text: str) -> bytes:
    """Text to speech, returned as MP3 bytes."""
    r = openai_client().audio.speech.create(
        model=config.TTS_MODEL,
        voice=config.TTS_VOICE,
        input=text[:4000],
        instructions=(
            "Speak as a warm, unhurried beauty-counter assistant in a light Indian English accent. "
            "Read prices in rupees naturally."
        ),
        response_format="mp3",
    )
    return r.content


def transcribe(audio: bytes, filename: str = "question.wav") -> str:
    r = openai_client().audio.transcriptions.create(
        model=config.STT_MODEL,
        file=(filename, audio),
        language="en",
        prompt="A shopper asking about beauty products, brands like Lakme, Maybelline, Biotique, Kay Beauty, Huda Beauty, prices in rupees.",
    )
    return r.text.strip()
