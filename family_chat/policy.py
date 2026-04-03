from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .config import ProfileConfig


KEYWORD_RULES = {
    "adult_sexual": [
        r"\bporn\b",
        r"\bhentai\b",
        r"\berotica\b",
        r"\bblowjob\b",
        r"\banal sex\b",
        r"\bsex tape\b",
        r"\bnude photos?\b",
    ],
    "graphic_violence": [
        r"\bbeheading\b",
        r"\bdismember(?:ed|ment)?\b",
        r"\bgore\b",
        r"\btorture\b",
    ],
    "drugs": [
        r"\bhow to make meth\b",
        r"\bcocaine\b",
        r"\bheroin\b",
        r"\bfentanyl\b",
    ],
    "self_harm": [
        r"\bhow to kill myself\b",
        r"\bhow to self[- ]harm\b",
        r"\bsuicide note\b",
    ],
    "hate": [
        r"\bhow to join a hate group\b",
        r"\bnazi propaganda\b",
    ],
}


@dataclass(frozen=True)
class GuardVerdict:
    safe: bool
    categories: Sequence[str]
    raw: str


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str = ""
    categories: Sequence[str] = ()


def parse_guard_output(text: str) -> GuardVerdict:
    cleaned = (text or "").strip()
    if not cleaned:
        return GuardVerdict(safe=False, categories=(), raw=cleaned)

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return GuardVerdict(safe=False, categories=(), raw=cleaned)

    verdict = lines[0].lower()
    categories: List[str] = []
    for line in lines[1:]:
        categories.extend(re.findall(r"\bS\d+\b", line))

    unique_categories = list(dict.fromkeys(categories))
    return GuardVerdict(safe=verdict == "safe", categories=unique_categories, raw=cleaned)


def blocked_keyword_categories(text: str, enabled_categories: Iterable[str]) -> List[str]:
    blocked: List[str] = []
    haystack = text.lower()
    for category in enabled_categories:
        patterns = KEYWORD_RULES.get(category, [])
        if any(re.search(pattern, haystack) for pattern in patterns):
            blocked.append(category)
    return blocked


def evaluate_text_for_profile(profile: ProfileConfig, text: str, verdict: GuardVerdict) -> PolicyDecision:
    keyword_hits = blocked_keyword_categories(text, profile.keyword_categories)
    if keyword_hits:
        return PolicyDecision(
            allowed=False,
            reason="keyword_policy",
            categories=tuple(keyword_hits),
        )

    if not verdict.safe:
        blocked = [code for code in verdict.categories if code in profile.blocked_guard_categories]
        if blocked or not verdict.categories:
            return PolicyDecision(
                allowed=False,
                reason="guard_policy",
                categories=tuple(blocked or verdict.categories),
            )

    return PolicyDecision(allowed=True)
