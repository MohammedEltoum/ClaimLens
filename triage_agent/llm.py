"""Provider client wrappers for Gemma 4."""

from __future__ import annotations

import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Literal

from .json_utils import extract_json


ProviderName = Literal["cerebras", "gemini"]

CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
CEREBRAS_DEFAULT_MODEL = "gemma-4-31b"
GEMINI_DEFAULT_MODEL = "gemma-4-31b-it"
DEFAULT_PROVIDER: ProviderName = "cerebras"
DEFAULT_MODEL = CEREBRAS_DEFAULT_MODEL
DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.DOTALL)


class MissingAPIKeyError(RuntimeError):
    """Raised when the selected provider API key is not configured."""


class GemmaClient:
    """Small wrapper around the OpenAI-compatible Cerebras chat API."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str = CEREBRAS_BASE_URL,
        temperature: float = 0.2,
        max_completion_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens

        resolved_key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not resolved_key:
            raise MissingAPIKeyError(
                "Set CEREBRAS_API_KEY in your environment or .env file before running the triage pipeline."
            )

        try:
            import openai
        except ImportError as exc:
            raise RuntimeError("Install dependencies with `pip install -r requirements.txt`.") from exc

        self._client = openai.OpenAI(base_url=base_url, api_key=resolved_key)

    def chat_text(self, messages: List[Dict[str, Any]]) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_completion_tokens=self.max_completion_tokens,
        )
        return response.choices[0].message.content or ""

    def chat_json(self, messages: List[Dict[str, Any]]) -> Any:
        raw_text = self.chat_text(messages)
        return extract_json(raw_text)


class GeminiGemmaClient:
    """Google GenAI client wrapper for Gemma 4."""

    def __init__(
        self,
        *,
        model: str = GEMINI_DEFAULT_MODEL,
        api_key: str | None = None,
        temperature: float = 0.2,
        max_completion_tokens: int = 4096,
        thinking_level: str = "HIGH",
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.thinking_level = thinking_level

        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key:
            raise MissingAPIKeyError(
                "Set GEMINI_API_KEY in your environment or .env file before running with Gemini."
            )

        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install dependencies with `pip install -r requirements.txt`.") from exc

        self._client = genai.Client(api_key=resolved_key)

    def chat_text(self, messages: List[Dict[str, Any]]) -> str:
        from google.genai import types

        system_instruction, contents = _messages_to_gemini_contents(messages, types)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            temperature=self.temperature,
            max_output_tokens=self.max_completion_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
        )
        chunks = self._client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        )
        return "".join(chunk.text or "" for chunk in chunks)

    def chat_json(self, messages: List[Dict[str, Any]]) -> Any:
        raw_text = self.chat_text(messages)
        return extract_json(raw_text)


def create_llm_client(
    *,
    provider: ProviderName = DEFAULT_PROVIDER,
    model: str | None = None,
    api_key: str | None = None,
) -> GemmaClient | GeminiGemmaClient:
    resolved_provider = normalize_provider(provider)
    if resolved_provider == "gemini":
        return GeminiGemmaClient(model=model or GEMINI_DEFAULT_MODEL, api_key=api_key)
    return GemmaClient(model=model or CEREBRAS_DEFAULT_MODEL, api_key=api_key)


def normalize_provider(provider: str) -> ProviderName:
    normalized = provider.strip().lower()
    if normalized in {"cerebras", "cerebras api"}:
        return "cerebras"
    if normalized in {"gemini", "google", "google gemini", "gemini api"}:
        return "gemini"
    raise ValueError("Provider must be either 'cerebras' or 'gemini'.")


def load_dotenv_if_available() -> None:
    """Load a local .env when python-dotenv is installed."""

    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def image_data_url(image_path: str | Path) -> str:
    path = Path(image_path)
    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        mime_type = "image/png"

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def parse_data_url(data_url: str) -> tuple[str, bytes]:
    match = DATA_URL_RE.match(data_url)
    if not match:
        raise ValueError("Expected an image data URL.")
    return match.group("mime"), base64.b64decode(match.group("data"), validate=True)


def _messages_to_gemini_contents(messages: List[Dict[str, Any]], types: Any) -> tuple[str, List[Any]]:
    system_parts: list[str] = []
    contents: list[Any] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_parts.append(_content_to_text(content))
            continue
        gemini_role = "model" if role == "assistant" else "user"
        parts = _content_to_gemini_parts(content, types)
        contents.append(types.Content(role=gemini_role, parts=parts))
    return "\n\n".join(part for part in system_parts if part), contents


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(str(part.get("text", "")))
        return "\n".join(text_parts)
    return str(content)


def _content_to_gemini_parts(content: Any, types: Any) -> List[Any]:
    if isinstance(content, str):
        return [types.Part.from_text(text=content)]

    parts = []
    for part in content:
        if not isinstance(part, dict):
            parts.append(types.Part.from_text(text=str(part)))
            continue
        if part.get("type") == "text":
            parts.append(types.Part.from_text(text=str(part.get("text", ""))))
        elif part.get("type") == "image_url":
            data_url = part.get("image_url", {}).get("url", "")
            mime_type, image_bytes = parse_data_url(data_url)
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
    return parts
