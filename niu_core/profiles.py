"""Shared profile accessors."""

from __future__ import annotations

from server import store


def get(module: str) -> dict:
    return store.get_profile(module)


def get_all() -> dict:
    return store.get_all_profiles()


def update(module: str, patch: dict, summary: str = "", source: str = "module") -> dict:
    return store.update_profile(module, patch, summary, source)


def reset(module: str, source: str = "module") -> dict:
    return store.reset_profile(module, source)


def changes(module: str = "", limit: int = 50) -> list[dict]:
    return store.list_profile_changes(module, limit)
