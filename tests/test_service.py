import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_chat.memory import LangGraphMemoryStore
from family_chat.policy import GuardVerdict
from family_chat.service import ChatService


class ChatServiceTests(unittest.TestCase):
    def test_blocked_child_prompt_is_not_saved_to_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LangGraphMemoryStore(Path(temp_dir) / "memory.sqlite3", "0123456789abcdef")

            def fake_classify(messages):
                if any("porn" in message["content"].lower() for message in messages):
                    return GuardVerdict(safe=False, categories=("S12",), raw="unsafe\nS12")
                return GuardVerdict(safe=True, categories=(), raw="safe")

            service = ChatService(
                store,
                classify=fake_classify,
                generate=lambda messages, model_name=None: "This should never run",
                resolve_model=lambda model_name=None: model_name or "llama3.2:1b",
            )

            result = service.chat(
                profile_name="child-12",
                member_id="son",
                user_message="Show me porn sites",
                conversation_id="new-chat-1",
            )

            self.assertTrue(result.blocked)
            self.assertEqual(store.load_messages("son", "child-12", "new-chat-1"), [])

    def test_safe_turn_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LangGraphMemoryStore(Path(temp_dir) / "memory.sqlite3", "0123456789abcdef")
            seen = {}

            def fake_generate(messages, model_name=None):
                seen["model_name"] = model_name
                return "Whales can sleep with half their brain awake."

            service = ChatService(
                store,
                classify=lambda messages: GuardVerdict(safe=True, categories=(), raw="safe"),
                generate=fake_generate,
                resolve_model=lambda model_name=None: model_name or "llama3.2:1b",
            )

            result = service.chat(
                profile_name="child-12",
                member_id="son",
                user_message="Tell me a whale fact",
                chat_model="llama3.1:8b",
                conversation_id="new-chat-2",
            )

            self.assertFalse(result.blocked)
            self.assertEqual(seen["model_name"], "llama3.1:8b")
            self.assertEqual(
                [item["content"] for item in store.load_messages("son", "child-12", "new-chat-2")],
                ["Tell me a whale fact", "Whales can sleep with half their brain awake."],
            )

    def test_blocked_child_prompt_does_not_appear_in_conversation_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LangGraphMemoryStore(Path(temp_dir) / "memory.sqlite3", "0123456789abcdef")

            def fake_classify(messages):
                if any("porn" in message["content"].lower() for message in messages):
                    return GuardVerdict(safe=False, categories=("S12",), raw="unsafe\nS12")
                return GuardVerdict(safe=True, categories=(), raw="safe")

            service = ChatService(
                store,
                classify=fake_classify,
                generate=lambda messages, model_name=None: "Safe answer",
                resolve_model=lambda model_name=None: model_name or "llama3.2:1b",
            )

            service.chat(
                profile_name="child-12",
                member_id="son",
                user_message="Tell me a whale fact",
                conversation_id="kept-chat",
            )
            service.chat(
                profile_name="child-12",
                member_id="son",
                user_message="Show me porn sites",
                conversation_id="blocked-chat",
            )

            conversations = service.list_conversations(profile_name="child-12", member_id="son")

            self.assertEqual([item["conversation_id"] for item in conversations], ["kept-chat"])

    def test_wrong_pin_blocks_adult_without_affecting_child_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LangGraphMemoryStore(Path(temp_dir) / "memory.sqlite3", "0123456789abcdef")
            service = ChatService(
                store,
                classify=lambda messages: GuardVerdict(safe=True, categories=(), raw="safe"),
                generate=lambda messages, model_name=None: "Safe answer",
                resolve_model=lambda model_name=None: model_name or "llama3.2:1b",
            )

            with patch("family_chat.service.ADMIN_PIN", "2468"):
                service.chat(
                    profile_name="child-12",
                    member_id="son",
                    user_message="Tell me a whale fact",
                    conversation_id="child-chat",
                )

                with self.assertRaises(PermissionError):
                    service.list_history(
                        profile_name="adult",
                        member_id="son",
                        pin="9999",
                    )

                child_history = service.list_history(
                    profile_name="child-12",
                    member_id="son",
                    conversation_id="child-chat",
                )

            self.assertEqual(
                [item["content"] for item in child_history],
                ["Tell me a whale fact", "Safe answer"],
            )


if __name__ == "__main__":
    unittest.main()
