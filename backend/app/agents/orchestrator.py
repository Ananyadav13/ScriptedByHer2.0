"""Shared agent orchestration. Phase 1: smoke test only (proves key + tool runner).

Real Agent 1/2 loops arrive in Phase 2/4.
"""
from anthropic import Anthropic, beta_tool

from ..config import settings


@beta_tool
def echo(text: str) -> str:
    """Echo back the given text (smoke-test tool).

    Args:
        text: The text to echo.
    """
    return f"ECHO: {text}"


def smoke_test() -> str:
    """One tool-runner round trip. Returns Claude's final text."""
    client = Anthropic(api_key=settings.anthropic_api_key)
    runner = client.beta.messages.tool_runner(
        model=settings.llm_model,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        tools=[echo],
        messages=[{
            "role": "user",
            "content": "Call the echo tool with the text 'build-trust-online', then confirm in one short sentence.",
        }],
    )
    final = ""
    for message in runner:
        for block in message.content:
            if block.type == "text":
                final = block.text
    return final or "(no text returned)"
