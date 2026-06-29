"""Local web UI server for the triage console."""

from __future__ import annotations

import argparse
import base64
import json
import re
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .orchestrator import TriagePipeline


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = PROJECT_ROOT / "ui"
UPLOAD_ROOT = PROJECT_ROOT / "outputs" / "uploads"
MAX_REQUEST_BYTES = 20 * 1024 * 1024

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

IMAGE_SUFFIXES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

DATA_URL_RE = re.compile(r"^data:(?P<mime>image/(?:png|jpeg|webp|gif));base64,(?P<data>.+)$")


class TriageUIHandler(BaseHTTPRequestHandler):
    server_version = "TriageUI/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True})
            return
        if parsed.path in {"/", "/ui"}:
            self._send_file(UI_ROOT / "index.html")
            return

        requested = unquote(parsed.path.lstrip("/"))
        candidate = (PROJECT_ROOT / requested).resolve()
        if not _is_allowed_static_path(candidate):
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return
        self._send_file(candidate)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/triage":
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json()
            complaint = str(payload.get("complaint", "")).strip()
            image_path = _resolve_image_input(payload)
            result = TriagePipeline().run(image_path=image_path, complaint=complaint)
            self._send_json(result.to_dict())
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Request body is required.")
        if content_length > MAX_REQUEST_BYTES:
            raise ValueError("Request body is too large.")

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", MIME_TYPES.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _is_allowed_static_path(path: Path) -> bool:
    allowed_roots = [UI_ROOT.resolve()]
    allowed_files = [(PROJECT_ROOT / "radio2.png").resolve(), (PROJECT_ROOT / "OIP.webp").resolve()]
    return any(_is_relative_to(path, root) for root in allowed_roots) or path in allowed_files


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_image_input(payload: dict[str, Any]) -> Path:
    data_url = payload.get("image_data_url")
    if not data_url:
        sample_path = PROJECT_ROOT / "radio2.png"
        if sample_path.exists():
            return sample_path
        raise ValueError("image_data_url is required when the sample image is unavailable.")

    image_bytes, suffix = decode_image_data_url(str(data_url))
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    image_path = UPLOAD_ROOT / f"{uuid.uuid4().hex}{suffix}"
    image_path.write_bytes(image_bytes)
    return image_path


def decode_image_data_url(data_url: str) -> tuple[bytes, str]:
    match = DATA_URL_RE.match(data_url)
    if not match:
        raise ValueError("image_data_url must be a base64 PNG, JPEG, WebP, or GIF data URL.")

    mime_type = match.group("mime")
    suffix = IMAGE_SUFFIXES[mime_type]
    try:
        image_bytes = base64.b64decode(match.group("data"), validate=True)
    except ValueError as exc:
        raise ValueError("image_data_url contains invalid base64 data.") from exc
    if not image_bytes:
        raise ValueError("image_data_url is empty.")
    return image_bytes, suffix


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local support triage UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), TriageUIHandler)
    print(f"ClaimLens Triage running at http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
