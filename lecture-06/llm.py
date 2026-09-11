"""Shared Claude API helper for the Lecture 06 planning-pattern demos.

Every demo script in this folder imports from here so the client setup,
error handling, and text-extraction boilerplate live in exactly one place
instead of being copy-pasted into each pattern file.

Requires ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN, or an `ant auth login`
profile) in the environment. Get a key at
https://console.anthropic.com/settings/keys
"""
from __future__ import annotations

import os
import sys

import anthropic

DEFAULT_MODEL = "claude-opus-5"

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    """Lazily build the client so `import llm` never requires a key."""
    global _client
    if _client is None:
        if not (
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        ):
            sys.exit(
                "ANTHROPIC_API_KEY is not set.\n"
                "Get a key at https://console.anthropic.com/settings/keys and run:\n"
                "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            )
        _client = anthropic.Anthropic()
    return _client


def ask(
    user: str,
    *,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    temperature: float | None = None,
    effort: str | None = None,
) -> str:
    """One-shot text completion. Returns the concatenated text blocks.

    `temperature` and `effort` are both optional and mutually relevant to
    different models - see the docstring in each pattern file for which one
    it passes and why (e.g. Claude Haiku 4.5 supports `temperature` but
    errors on `effort`; Claude Opus 5 is the reverse).
    """
    kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": user}],
    )
    if system:
        kwargs["system"] = system
    if temperature is not None:
        kwargs["temperature"] = temperature
    if effort is not None:
        kwargs["output_config"] = {"effort": effort}

    response = client().messages.create(**kwargs)
    return "".join(b.text for b in response.content if b.type == "text").strip()


def ask_full(
    messages: list[dict],
    *,
    system: str | None = None,
    tools: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    effort: str | None = None,
):
    """Full-response version for callers that need tool_use blocks,
    stop_reason, etc. (the ReAct executor inside Plan-and-Execute)."""
    kwargs: dict = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    if effort is not None:
        kwargs["output_config"] = {"effort": effort}
    return client().messages.create(**kwargs)
