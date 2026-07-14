"""Deterministic logic only — NO LLM imports anywhere in this package.

These are plain, testable functions the agent calls as tools. Keeping them
LLM-free is a deliberate design signal (Code Quality rubric) and lets Phase 4
unit-test every decision rule.
"""
