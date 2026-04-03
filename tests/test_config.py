import importlib
import os
import unittest
from unittest.mock import patch

import family_chat.config as config_module


class ConfigTests(unittest.TestCase):
    def tearDown(self) -> None:
        importlib.reload(config_module)

    def _load_snapshot(self, env: dict[str, str]) -> dict[str, object]:
        base_env = {
            "FAMILY_CHAT_ADMIN_PIN": "",
            "FAMILY_CHAT_MODEL_PULL_REQUIRES_PIN": "",
        }
        base_env.update(env)
        with patch.dict(os.environ, base_env, clear=True):
            module = importlib.reload(config_module)
            return {
                "valid_members": module.VALID_MEMBER_IDS,
                "device_member": module.DEVICE_MEMBER_ID,
                "settings": module.public_settings(),
            }

    def test_device_member_defaults_to_first_valid_member(self) -> None:
        snapshot = self._load_snapshot(
            {
                "FAMILY_CHAT_MEMBERS": "parent-b,son",
                "FAMILY_CHAT_DEVICE_MEMBER": "",
            }
        )

        self.assertEqual(snapshot["valid_members"], ("parent-b", "son"))
        self.assertEqual(snapshot["device_member"], "parent-b")
        self.assertEqual(snapshot["settings"]["device_member"]["id"], "parent-b")
        self.assertNotIn("members", snapshot["settings"])

    def test_device_member_falls_back_to_son_when_member_list_is_invalid(self) -> None:
        snapshot = self._load_snapshot(
            {
                "FAMILY_CHAT_MEMBERS": "!!!,@@@",
                "FAMILY_CHAT_DEVICE_MEMBER": "",
            }
        )

        self.assertEqual(snapshot["valid_members"], ("son",))
        self.assertEqual(snapshot["device_member"], "son")

    def test_invalid_device_member_raises_at_config_load(self) -> None:
        with patch.dict(
            os.environ,
            {
                "FAMILY_CHAT_MEMBERS": "son,parent-a",
                "FAMILY_CHAT_DEVICE_MEMBER": "parent-b",
            },
            clear=True,
        ):
            with self.assertRaises(RuntimeError):
                importlib.reload(config_module)

    def test_model_pull_requires_pin_only_when_flag_and_admin_pin_are_set(self) -> None:
        snapshot = self._load_snapshot(
            {
                "FAMILY_CHAT_MEMBERS": "son",
                "FAMILY_CHAT_DEVICE_MEMBER": "son",
                "FAMILY_CHAT_ADMIN_PIN": "4821",
                "FAMILY_CHAT_MODEL_PULL_REQUIRES_PIN": "1",
            }
        )

        self.assertTrue(snapshot["settings"]["model_pull_requires_pin"])

    def test_adult_profile_is_hidden_until_admin_pin_is_configured(self) -> None:
        snapshot = self._load_snapshot(
            {
                "FAMILY_CHAT_MEMBERS": "son",
                "FAMILY_CHAT_DEVICE_MEMBER": "son",
            }
        )

        self.assertIn("child-12", snapshot["settings"]["profiles"])
        self.assertNotIn("adult", snapshot["settings"]["profiles"])

    def test_adult_profile_is_exposed_when_admin_pin_is_configured(self) -> None:
        snapshot = self._load_snapshot(
            {
                "FAMILY_CHAT_MEMBERS": "son",
                "FAMILY_CHAT_DEVICE_MEMBER": "son",
                "FAMILY_CHAT_ADMIN_PIN": "4821",
            }
        )

        self.assertIn("adult", snapshot["settings"]["profiles"])
        self.assertTrue(snapshot["settings"]["profiles"]["adult"]["requires_pin"])


if __name__ == "__main__":
    unittest.main()
