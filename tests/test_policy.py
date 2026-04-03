import unittest

from family_chat.config import PROFILES
from family_chat.policy import evaluate_text_for_profile, parse_guard_output


class PolicyTests(unittest.TestCase):
    def test_parse_safe_output(self) -> None:
        verdict = parse_guard_output("safe")
        self.assertTrue(verdict.safe)
        self.assertEqual(list(verdict.categories), [])

    def test_parse_unsafe_output(self) -> None:
        verdict = parse_guard_output("unsafe\nS12\nS11")
        self.assertFalse(verdict.safe)
        self.assertEqual(list(verdict.categories), ["S12", "S11"])

    def test_child_profile_blocks_keyword_hits(self) -> None:
        verdict = parse_guard_output("safe")
        decision = evaluate_text_for_profile(PROFILES["child-12"], "Show me porn sites", verdict)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "keyword_policy")

    def test_child_profile_blocks_guard_categories(self) -> None:
        verdict = parse_guard_output("unsafe\nS12")
        decision = evaluate_text_for_profile(PROFILES["child-12"], "normal text", verdict)
        self.assertFalse(decision.allowed)
        self.assertEqual(list(decision.categories), ["S12"])

    def test_clean_child_message_passes(self) -> None:
        verdict = parse_guard_output("safe")
        decision = evaluate_text_for_profile(PROFILES["child-12"], "Tell me a fun fact about whales", verdict)
        self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
