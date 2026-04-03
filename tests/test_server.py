import io
import json
import unittest
from http import HTTPStatus
from unittest.mock import patch

import family_chat.server as server_module
from family_chat.service import ChatResult


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def chat(self, **kwargs):
        self.calls.append(("chat", kwargs))
        return ChatResult(blocked=False, reply="Safe reply")

    def list_history(self, **kwargs):
        self.calls.append(("history", kwargs))
        return [{"role": "assistant", "content": "Ready"}]


class ServerTests(unittest.TestCase):
    def _build_handler(self, payload: dict) -> tuple[server_module.FamilyChatHandler, dict]:
        captured: dict = {}
        handler = server_module.FamilyChatHandler.__new__(server_module.FamilyChatHandler)
        handler._read_json_body = lambda: payload

        def send_json(response_payload, status=HTTPStatus.OK):
            captured["payload"] = response_payload
            captured["status"] = status

        handler._send_json = send_json
        return handler, captured

    def _build_stream_handler(self, payload: dict) -> tuple[server_module.FamilyChatHandler, dict]:
        captured: dict = {"headers": []}
        handler = server_module.FamilyChatHandler.__new__(server_module.FamilyChatHandler)
        handler._read_json_body = lambda: payload
        handler.wfile = io.BytesIO()
        handler.send_response = lambda status: captured.__setitem__("status", status)
        handler.send_header = lambda name, value: captured["headers"].append((name, value))
        handler.end_headers = lambda: captured.__setitem__("ended", True)
        return handler, captured

    def test_chat_uses_configured_device_member_not_request_member(self) -> None:
        fake_service = RecordingService()
        handler, captured = self._build_handler(
            {
                "member_id": "son",
                "profile": "child-12",
                "message": "Tell me a whale fact",
                "conversation_id": "chat-1",
            }
        )

        with patch.object(server_module, "DEVICE_MEMBER_ID", "parent-a"), patch.object(
            server_module, "get_chat_service", return_value=fake_service
        ):
            handler._handle_chat()

        self.assertEqual(captured["status"], HTTPStatus.OK)
        self.assertEqual(captured["payload"]["reply"], "Safe reply")
        self.assertEqual(fake_service.calls[0][0], "chat")
        self.assertEqual(fake_service.calls[0][1]["member_id"], "parent-a")

    def test_history_uses_configured_device_member_not_request_member(self) -> None:
        fake_service = RecordingService()
        handler, captured = self._build_handler(
            {
                "member_id": "son",
                "profile": "child-12",
                "conversation_id": "chat-2",
            }
        )

        with patch.object(server_module, "DEVICE_MEMBER_ID", "parent-b"), patch.object(
            server_module, "get_chat_service", return_value=fake_service
        ):
            handler._handle_history()

        self.assertEqual(captured["status"], HTTPStatus.OK)
        self.assertEqual(captured["payload"]["messages"][0]["content"], "Ready")
        self.assertEqual(fake_service.calls[0][0], "history")
        self.assertEqual(fake_service.calls[0][1]["member_id"], "parent-b")

    def test_pull_model_progress_streams_progress_and_completion_events(self) -> None:
        handler, captured = self._build_stream_handler({"model_name": "llama3.2:3b"})
        selector_state = {
            "default_chat_model": "llama3.2:1b",
            "ollama_available": True,
            "ollama_error": "",
            "chat_models": [{"name": "llama3.2:3b", "installed": True}],
        }

        with patch.object(
            server_module,
            "stream_pull_chat_model",
            return_value=iter(
                [
                    {"type": "progress", "status": "pulling manifest", "completed": None, "total": None},
                    {"type": "progress", "status": "downloading", "completed": 50, "total": 100},
                ]
            ),
        ), patch.object(server_module, "model_selector_state", return_value=selector_state):
            handler._handle_pull_model_progress()

        self.assertEqual(captured["status"], HTTPStatus.OK)
        lines = [
            json.loads(line)
            for line in handler.wfile.getvalue().decode("utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(lines[0]["type"], "progress")
        self.assertEqual(lines[1]["status"], "downloading")
        self.assertEqual(lines[-1]["type"], "complete")
        self.assertEqual(lines[-1]["selector_state"]["chat_models"][0]["name"], "llama3.2:3b")


if __name__ == "__main__":
    unittest.main()
