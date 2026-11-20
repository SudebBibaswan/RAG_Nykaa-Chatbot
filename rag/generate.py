"""Grounded answer generation, streamed token by token (OpenAI or Claude via rag.llm)."""
from __future__ import annotations

from typing import Iterator

from . import config, llm, prompts
from .schemas import Aggregate, Record


def stream_answer(
    question: str,
    records: list[Record],
    aggregates: list[Aggregate],
    unsupported: list[str],
    history: list[dict] | None = None,
    operation: str = "lookup",
) -> Iterator[str]:
    """Yields text deltas. Raises llm.Refusal if the model declines."""
    messages: list[dict] = []
    for turn in (history or [])[-config.HISTORY_TURNS * 2 :]:
        if turn["role"] in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    # history must start with a user turn
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": prompts.generator_user(question, records, aggregates, unsupported)})
    yield from llm.stream(
        prompts.GENERATOR_SYSTEM,
        messages,
        model=config.CHAT_MODEL,
        # comparisons and rankings need the model to actually compare numbers
        effort=config.COMPARE_EFFORT if operation in ("compare", "rank") else config.CHAT_EFFORT,
        max_tokens=config.MAX_ANSWER_TOKENS * 4,  # headroom for reasoning tokens
    )
