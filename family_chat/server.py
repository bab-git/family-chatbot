from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from .config import MEMORY_DB_PATH, SERVER_HOST, SERVER_PORT, public_settings
from .memory import LangGraphMemoryStore, MemoryConfigurationError
from .ollama_client import OllamaError, model_selector_state
from .service import ChatService


STATIC_INDEX = Path(__file__).resolve().parent.parent / "static" / "index.html"
SERVICE: ChatService | None = None


def get_chat_service() -> ChatService:
    global SERVICE
    if SERVICE is None:
        key = os.getenv("LANGGRAPH_AES_KEY", "")
        if not key:
            raise MemoryConfigurationError(
                "LANGGRAPH_AES_KEY is not set. Add it to your shell or local .env file before starting the server."
            )
        SERVICE = ChatService(LangGraphMemoryStore(MEMORY_DB_PATH, key))
    return SERVICE


class FamilyChatHandler(BaseHTTPRequestHandler):
    server_version = "FamilyChatMVP/0.2"

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._serve_index()
            return
        if self.path == "/api/settings":
            payload = public_settings()
            payload.update(model_selector_state())
            self._send_json(payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/chat":
            self._handle_chat()
            return
        if self.path == "/api/history":
            self._handle_history()
            return
        if self.path == "/api/conversations":
            self._handle_conversations()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _serve_index(self) -> None:
        body = STATIC_INDEX.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_chat(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        user_message = str(payload.get("message", "")).strip()
        if not user_message:
            self._send_json({"error": "Message is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            result = get_chat_service().chat(
                profile_name=str(payload.get("profile", "child-12")),
                member_id=str(payload.get("member_id", "son")),
                pin=str(payload.get("pin", "")),
                user_message=user_message,
                chat_model=str(payload.get("chat_model", "")).strip() or None,
                conversation_id=str(payload.get("conversation_id", "")).strip() or None,
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except PermissionError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.FORBIDDEN)
            return
        except MemoryConfigurationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.SERVICE_UNAVAILABLE)
            return
        except OllamaError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return

        self._send_json(
            {
                "blocked": result.blocked,
                "reason": result.reason,
                "categories": list(result.categories),
                "reply": result.reply,
                "conversation_id": str(payload.get("conversation_id", "")).strip() or "default",
            }
        )

    def _handle_history(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            messages = get_chat_service().list_history(
                profile_name=str(payload.get("profile", "child-12")),
                member_id=str(payload.get("member_id", "son")),
                pin=str(payload.get("pin", "")),
                conversation_id=str(payload.get("conversation_id", "")).strip() or None,
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except PermissionError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.FORBIDDEN)
            return
        except MemoryConfigurationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.SERVICE_UNAVAILABLE)
            return

        self._send_json(
            {
                "messages": messages,
                "conversation_id": str(payload.get("conversation_id", "")).strip() or "default",
            }
        )

    def _handle_conversations(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            conversations = get_chat_service().list_conversations(
                profile_name=str(payload.get("profile", "child-12")),
                member_id=str(payload.get("member_id", "son")),
                pin=str(payload.get("pin", "")),
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except PermissionError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.FORBIDDEN)
            return
        except MemoryConfigurationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.SERVICE_UNAVAILABLE)
            return

        self._send_json({"conversations": conversations})


def main() -> None:
    server = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), FamilyChatHandler)
    print(f"Family Chat MVP listening on http://{SERVER_HOST}:{SERVER_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
