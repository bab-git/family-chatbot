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


if __name__ == "__main__":
    unittest.main()
