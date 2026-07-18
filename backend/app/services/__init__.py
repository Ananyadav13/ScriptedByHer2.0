"""Deterministic logic only — NO LLM imports anywhere in this package.

These are plain, testable functions the agent calls as tools. Keeping them
LLM-free is deliberate: every decision rule stays unit-testable without a
network call or an API key.
"""
