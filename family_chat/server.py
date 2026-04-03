from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from .config import (
    ADMIN_PIN,
    DEVICE_MEMBER_ID,
    MEMORY_DB_PATH,
    MODEL_PULL_REQUIRES_PIN,
    SERVER_HOST,
    SERVER_PORT,
    public_settings,
)
from .memory import LangGraphMemoryStore, MemoryConfigurationError
from .ollama_client import (
    OllamaError,
    delete_chat_model,
    model_selector_state,
    pull_chat_model,
    stream_pull_chat_model,
)
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
    server_version = "FamilyChatExperiment/0.4"

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._serve_index()
            return
        if self.path == "/api/settings":
            self._handle_settings()
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
        if self.path == "/api/pull-model":
            self._handle_pull_model()
            return
        if self.path == "/api/delete-model":
            self._handle_delete_model()
            return
        if self.path == "/api/pull-model-progress":
            self._handle_pull_model_progress()
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
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _begin_json_stream(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def _write_json_stream_event(self, payload: Dict[str, Any]) -> None:
        line = json.dumps(payload).encode("utf-8") + b"\n"
        self.wfile.write(line)
        self.wfile.flush()

    def _handle_settings(self) -> None:
        payload = public_settings()
        payload.update(model_selector_state())
        self._send_json(payload)

    @staticmethod
    def _require_model_pull_pin(pin: str) -> None:
        if MODEL_PULL_REQUIRES_PIN and ADMIN_PIN and pin != ADMIN_PIN:
            raise PermissionError("Pulling models requires the correct adult PIN.")

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

        conversation_id = str(payload.get("conversation_id", "")).strip() or "default"

        try:
            result = get_chat_service().chat(
                profile_name=str(payload.get("profile", "child-12")),
                member_id=DEVICE_MEMBER_ID,
                pin=str(payload.get("pin", "")),
                user_message=user_message,
                chat_model=str(payload.get("chat_model", "")).strip() or None,
                conversation_id=conversation_id,
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
                "conversation_id": conversation_id,
            }
        )

    def _handle_history(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        conversation_id = str(payload.get("conversation_id", "")).strip() or "default"

        try:
            messages = get_chat_service().list_history(
                profile_name=str(payload.get("profile", "child-12")),
                member_id=DEVICE_MEMBER_ID,
                pin=str(payload.get("pin", "")),
                conversation_id=conversation_id,
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

        self._send_json({"messages": messages, "conversation_id": conversation_id})

    def _handle_conversations(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            conversations = get_chat_service().list_conversations(
                profile_name=str(payload.get("profile", "child-12")),
                member_id=DEVICE_MEMBER_ID,
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

    def _handle_pull_model(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        model_name = str(payload.get("model_name", "")).strip()
        if not model_name:
            self._send_json({"error": "Model name is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            self._require_model_pull_pin(str(payload.get("pin", "")))
            selector_state = pull_chat_model(model_name)
        except PermissionError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.FORBIDDEN)
            return
        except OllamaError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return

        selector_state["message"] = f"Model '{model_name}' is ready to use."
        self._send_json(selector_state)

    def _handle_delete_model(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        model_name = str(payload.get("model_name", "")).strip()
        if not model_name:
            self._send_json({"error": "Model name is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            selector_state = delete_chat_model(model_name)
        except OllamaError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return

        selector_state["message"] = f"Model '{model_name}' was deleted."
        self._send_json(selector_state)

    def _handle_pull_model_progress(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        model_name = str(payload.get("model_name", "")).strip()
        if not model_name:
            self._send_json({"error": "Model name is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            self._require_model_pull_pin(str(payload.get("pin", "")))
            events = stream_pull_chat_model(model_name)
        except PermissionError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.FORBIDDEN)
            return
        except OllamaError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            self._begin_json_stream()
            for event in events:
                self._write_json_stream_event(event)

            self._write_json_stream_event(
                {
                    "type": "complete",
                    "done": True,
                    "model_name": model_name,
                    "message": f"Model '{model_name}' is ready to use.",
                    "selector_state": model_selector_state(),
                }
            )
        except OllamaError as exc:
            try:
                self._write_json_stream_event({"type": "error", "done": True, "error": str(exc)})
            except OSError:
                return
        except OSError:
            return


def main() -> None:
    server = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), FamilyChatHandler)
    print(f"Family Chat Experiment listening on http://{SERVER_HOST}:{SERVER_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
