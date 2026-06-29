"""Helpers for working with model-produced JSON."""

from __future__ import annotations

import json
import re
from typing import Any


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class JSONExtractionError(ValueError):
    """Raised when a model response cannot be parsed as JSON."""


def extract_json(text: str) -> Any:
    """Extract and parse the first JSON object or array in a model response."""

    stripped = text.strip()
    fenced_match = _FENCED_JSON_RE.search(stripped)
    if fenced_match:
        stripped = fenced_match.group(1).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    candidate = _balanced_json_candidate(stripped)
    if candidate is None:
        raise JSONExtractionError("No JSON object or array found in model response.")

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise JSONExtractionError(f"Could not parse JSON from model response: {exc}") from exc


def _balanced_json_candidate(text: str) -> str | None:
    start = _first_json_start(text)
    if start is None:
        return None

    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def _first_json_start(text: str) -> int | None:
    starts = [idx for idx in (text.find("{"), text.find("[")) if idx != -1]
    if not starts:
        return None
    return min(starts)
