import unittest
from unittest.mock import patch

from family_chat.ollama_client import OllamaError, pull_chat_model


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


if __name__ == "__main__":
    unittest.main()
