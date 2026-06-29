"""Policy document loading helpers."""

from __future__ import annotations

from pathlib import Path


DEFAULT_POLICY_PATH = Path(__file__).resolve().parent.parent / "policy" / "support_policy.md"


def load_policy_text(policy_path: str | Path | None = None) -> str:
    path = Path(policy_path) if policy_path else DEFAULT_POLICY_PATH
    return path.read_text(encoding="utf-8").strip()
