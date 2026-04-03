import tempfile
import unittest
from pathlib import Path

from family_chat.memory import LangGraphMemoryStore


class MemoryTests(unittest.TestCase):
    def test_turns_are_isolated_by_member_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LangGraphMemoryStore(Path(temp_dir) / "memory.sqlite3", "0123456789abcdef")
            store.append_turn("son", "child-12", user_message="Hello", assistant_reply="Hi there")
            store.append_turn("parent-a", "adult", user_message="Adult hello", assistant_reply="Adult hi")

            son_history = store.load_messages("son", "child-12")
            adult_history = store.load_messages("parent-a", "adult")

            self.assertEqual([item["content"] for item in son_history], ["Hello", "Hi there"])
            self.assertEqual([item["content"] for item in adult_history], ["Adult hello", "Adult hi"])

    def test_turns_are_isolated_by_conversation_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LangGraphMemoryStore(Path(temp_dir) / "memory.sqlite3", "0123456789abcdef")
            store.append_turn(
                "son",
                "child-12",
                "default",
                user_message="Old chat hello",
                assistant_reply="Old chat hi",
            )
            store.append_turn(
                "son",
                "child-12",
                "new-chat-1",
                user_message="New chat hello",
                assistant_reply="New chat hi",
            )

            default_history = store.load_messages("son", "child-12", "default")
            new_chat_history = store.load_messages("son", "child-12", "new-chat-1")

            self.assertEqual([item["content"] for item in default_history], ["Old chat hello", "Old chat hi"])
            self.assertEqual([item["content"] for item in new_chat_history], ["New chat hello", "New chat hi"])

    def test_message_content_is_not_plaintext_in_sqlite_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "memory.sqlite3"
            marker = "super-secret-family-marker"
            store = LangGraphMemoryStore(db_path, "0123456789abcdef")
            store.append_turn("son", "child-12", user_message=marker, assistant_reply="safe reply")
            store.close()

            raw_bytes = db_path.read_bytes()
            self.assertNotIn(marker.encode("utf-8"), raw_bytes)

    def test_list_conversations_returns_recent_threads_for_selected_member_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LangGraphMemoryStore(Path(temp_dir) / "memory.sqlite3", "0123456789abcdef")
            store.append_turn(
                "son",
                "child-12",
                "default",
                user_message="Default hello",
                assistant_reply="Default hi",
            )
            store.append_turn(
                "son",
                "child-12",
                "new-chat-1",
                user_message="Dinosaurs are awesome",
                assistant_reply="They lived millions of years ago.",
            )
            store.append_turn(
                "parent-a",
                "adult",
                "adult-chat",
                user_message="Parent only",
                assistant_reply="Adult answer",
            )

            conversations = store.list_conversations("son", "child-12")

            self.assertEqual(
                [item["conversation_id"] for item in conversations],
                ["new-chat-1", "default"],
            )
            self.assertEqual(conversations[0]["title"], "Dinosaurs are awesome")
            self.assertEqual(conversations[0]["preview"], "They lived millions of years ago.")


if __name__ == "__main__":
    unittest.main()
