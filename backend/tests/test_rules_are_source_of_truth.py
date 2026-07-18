"""Guards the two invariants `services/rules.py` claims for itself.

These are drift tests, not behaviour tests. The failure they exist to catch is silent:
someone tunes a threshold in `rules.py`, the deterministic engine changes, and the agent
prompt keeps quoting the OLD number — so the agent reasons toward a verdict that
`_execute_action` then refuses to execute. Nothing crashes; the system just becomes
quietly incoherent, and the docs describing it become false.

Enforced here:
  1. every constant in rules.py is consumed by real code (no decorative thresholds)
  2. no threshold is duplicated as a literal in the prompts (prompts interpolate instead)
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
RULES = APP / "services" / "rules.py"
PROMPTS = APP / "agents" / "prompts.py"

# Constants deliberately exempt from the "must be consumed" rule, with the reason.
# Keep this empty if at all possible — an entry here is a promise to come back.
_EXEMPT: dict[str, str] = {}


def _defined_constants() -> list[str]:
    return re.findall(r"^([A-Z][A-Z0-9_]+)\s*=", RULES.read_text(encoding="utf8"), re.M)


def _app_source_excluding_rules() -> str:
    return "".join(
        p.read_text(encoding="utf8")
        for p in APP.rglob("*.py")
        if p.resolve() != RULES.resolve()
    )


def test_every_constant_is_consumed():
    """A threshold nobody reads is documentation pretending to be enforcement."""
    source = _app_source_excluding_rules()
    unused = [c for c in _defined_constants() if c not in source and c not in _EXEMPT]
    assert not unused, (
        "rules.py defines constants that no code reads: "
        f"{unused}. Either wire them into the implementation or delete them — "
        "an unused threshold implies a rule the system does not actually enforce."
    )


@pytest.mark.parametrize(
    "constant",
    ["BAN_RATING", "PRODUCT_HOLD_RATING", "INCONSISTENCY_EXEMPT_RATING",
     "MIN_ORDERS_FOR_ACTION", "SELLER_QC_SLA_DAYS"],
)
def test_prompt_quotes_the_live_value(constant):
    """The rendered prompt must contain each threshold's CURRENT value.

    Imported at call time so the value compared against is whatever rules.py holds now,
    not a number copied into this test.
    """
    from app.agents.prompts import AGENT1_SYSTEM_PROMPT
    from app.services import rules

    value = getattr(rules, constant)
    rendered = f"{value:g}" if isinstance(value, float) else str(value)
    assert rendered in AGENT1_SYSTEM_PROMPT, (
        f"{constant} is {value} in rules.py but that value does not appear in the "
        "agent prompt — the prompt and the deterministic engine have drifted apart."
    )


def test_prompts_interpolate_rather_than_hardcode():
    """prompts.py must import its thresholds, and must not restate them as literals."""
    text = PROMPTS.read_text(encoding="utf8")

    assert "from ..services.rules import" in text, (
        "prompts.py no longer imports from rules.py — thresholds have been inlined."
    )

    # The prompt body is an f-string; a bare threshold literal in the source means
    # someone typed the number instead of interpolating the constant.
    body = text.split("AGENT1_SYSTEM_PROMPT", 1)[1]
    for literal in ("3.8", "2.0", "3.0", ">= 20 orders", "within 7 days"):
        assert literal not in body, (
            f"prompts.py hardcodes {literal!r}. Interpolate the rules.py constant "
            "instead, so tuning the rule updates the prompt too."
        )
