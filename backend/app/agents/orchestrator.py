"""Shared agent orchestration. Phase 1: smoke test only (proves key + tool loop).

Gemini pivot (14 Jul 2026): replaces the Anthropic tool_runner with the
google-genai SDK. Equivalents used across the project:
  - Anthropic tool_runner   -> automatic function calling (pass Python fns as `tools`)
  - messages.parse()        -> response_schema=<PydanticModel> + response.parsed
  - adaptive thinking       -> types.ThinkingConfig (added where reasoning matters)

Real Agent 1/2 loops arrive in Phase 2/4. Note for Phase 2: to stream per-tool-call
events over SSE we will run the function-calling loop MANUALLY (inspect
response.function_calls, execute, feed results back) rather than the automatic
helper used here, so each tool call can be pushed to the event queue as it happens.
"""
from google import genai
from google.genai import types

from ..config import settings


def echo(text: str) -> str:
    """Echo back the given text (smoke-test tool).

    Args:
        text: The text to echo.
    """
    return f"ECHO: {text}"


def smoke_test() -> str:
    """One automatic-function-calling round trip. Returns Gemini's final text."""
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.llm_model,
        contents=(
            "Call the echo tool with the text 'build-trust-online', "
            "then confirm in one short sentence."
        ),
        config=types.GenerateContentConfig(tools=[echo]),
    )
    return response.text or "(no text returned)"
