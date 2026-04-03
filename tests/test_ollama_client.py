import unittest
from unittest.mock import patch

from family_chat.ollama_client import OllamaError, delete_chat_model, pull_chat_model, stream_pull_chat_model


class OllamaClientTests(unittest.TestCase):
    @patch("family_chat.ollama_client.model_selector_state")
    @patch("family_chat.ollama_client._post_json")
    def test_pull_chat_model_calls_ollama_and_returns_refreshed_selector_state(
        self, mock_post_json, mock_model_selector_state
    ) -> None:
        mock_post_json.return_value = {"status": "success"}
        mock_model_selector_state.return_value = {
            "default_chat_model": "llama3.2:1b",
            "ollama_available": True,
            "ollama_error": "",
            "chat_models": [{"name": "llama3.1:8b", "installed": True}],
        }

        result = pull_chat_model("llama3.1:8b")

        self.assertEqual(result["chat_models"][0]["name"], "llama3.1:8b")
        mock_post_json.assert_called_once_with(
            "/api/pull",
            {"model": "llama3.1:8b", "stream": False},
            timeout=3600,
        )

    def test_pull_chat_model_rejects_non_llama_models(self) -> None:
        with self.assertRaises(OllamaError):
            pull_chat_model("llama-guard3:1b")

    @patch("family_chat.ollama_client._iter_post_json_lines")
    def test_stream_pull_chat_model_yields_normalized_progress_events(self, mock_stream) -> None:
        mock_stream.return_value = iter(
            [
                {"status": "pulling manifest"},
                {
                    "status": "downloading",
                    "digest": "sha256:abc123",
                    "completed": 50,
                    "total": 100,
                },
                {"status": "success"},
            ]
        )

        events = list(stream_pull_chat_model("llama3.2:3b"))

        self.assertEqual(events[0]["type"], "progress")
        self.assertEqual(events[0]["status"], "pulling manifest")
        self.assertIsNone(events[0]["completed"])
        self.assertEqual(events[1]["digest"], "sha256:abc123")
        self.assertEqual(events[1]["completed"], 50)
        self.assertEqual(events[1]["total"], 100)
        mock_stream.assert_called_once_with("/api/pull", {"model": "llama3.2:3b"}, timeout=3600)

    @patch("family_chat.ollama_client._iter_post_json_lines")
    def test_stream_pull_chat_model_raises_on_stream_error(self, mock_stream) -> None:
        mock_stream.return_value = iter([{"error": "download failed"}])

        with self.assertRaises(OllamaError):
            list(stream_pull_chat_model("llama3.2:3b"))

    @patch("family_chat.ollama_client.model_selector_state")
    @patch("family_chat.ollama_client._delete_json")
    def test_delete_chat_model_calls_ollama_and_returns_refreshed_selector_state(
        self, mock_delete_json, mock_model_selector_state
    ) -> None:
        mock_delete_json.return_value = {}
        mock_model_selector_state.return_value = {
            "default_chat_model": "llama3.2:1b",
            "ollama_available": True,
            "ollama_error": "",
            "chat_models": [{"name": "llama3.2:3b", "installed": False}],
        }

        result = delete_chat_model("llama3.2:3b")

        self.assertFalse(result["chat_models"][0]["installed"])
        mock_delete_json.assert_called_once_with(
            "/api/delete",
            {"model": "llama3.2:3b"},
            timeout=120,
        )

    def test_delete_chat_model_rejects_non_llama_models(self) -> None:
        with self.assertRaises(OllamaError):
            delete_chat_model("llama-guard3:1b")


if __name__ == "__main__":
    unittest.main()
