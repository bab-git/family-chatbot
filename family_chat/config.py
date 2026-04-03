from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Tuple

from .env_loader import load_local_env


APP_ROOT = Path(__file__).resolve().parent.parent
load_local_env(APP_ROOT / ".env")


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    system_prompt: str
    blocked_guard_categories: FrozenSet[str]
    keyword_categories: Tuple[str, ...]
    fallback_message: str
    requires_pin: bool = False


CHAT_MODEL = os.getenv("FAMILY_CHAT_CHAT_MODEL", "llama3.2:1b")
GUARD_MODEL = os.getenv("FAMILY_CHAT_GUARD_MODEL", "llama-guard3:1b")
OLLAMA_URL = os.getenv("FAMILY_CHAT_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
SERVER_HOST = os.getenv("FAMILY_CHAT_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("FAMILY_CHAT_PORT", "8080"))
ADMIN_PIN = os.getenv("FAMILY_CHAT_ADMIN_PIN", "")
MOCK_OLLAMA = os.getenv("FAMILY_CHAT_MOCK_OLLAMA", "").lower() in {"1", "true", "yes"}
MEMORY_DB_PATH = Path(
    os.getenv("FAMILY_CHAT_DB_PATH", str(APP_ROOT / "data" / "family_chat_memory.sqlite3"))
).expanduser()
MEMORY_CONTEXT_LIMIT = int(os.getenv("FAMILY_CHAT_MEMORY_CONTEXT_LIMIT", "16"))
HISTORY_LOAD_LIMIT = int(os.getenv("FAMILY_CHAT_HISTORY_LOAD_LIMIT", "40"))
CONVERSATION_LIST_LIMIT = int(os.getenv("FAMILY_CHAT_CONVERSATION_LIST_LIMIT", "20"))
RAW_MEMBER_IDS = os.getenv("FAMILY_CHAT_MEMBERS", "son,parent-a,parent-b")


def _parse_member_ids(raw_value: str) -> Tuple[str, ...]:
    members = []
    for raw_member in raw_value.split(","):
        member = raw_member.strip().lower()
        if not member:
            continue
        if any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in member):
            continue
        if member not in members:
            members.append(member)

    if not members:
        members = ["son"]
    return tuple(members)


VALID_MEMBER_IDS = _parse_member_ids(RAW_MEMBER_IDS)


def member_label(member_id: str) -> str:
    return member_id.replace("-", " ").replace("_", " ").title()

ALL_GUARD_CATEGORIES = frozenset(
    {
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "S7",
        "S8",
        "S9",
        "S10",
        "S11",
        "S12",
        "S13",
    }
)

CHILD_GUARD_CATEGORIES = frozenset(
    {
        "S1",
        "S2",
        "S3",
        "S4",
        "S6",
        "S7",
        "S9",
        "S10",
        "S11",
        "S12",
        "S13",
    }
)

PROFILES: Dict[str, ProfileConfig] = {
    "child-12": ProfileConfig(
        name="child-12",
        system_prompt=(
            "You are a family-safe assistant for a 12-year-old child. "
            "Use clear, calm, age-appropriate language. "
            "Do not provide explicit sexual content, graphic violence, self-harm content, "
            "hate content, illegal instructions, dangerous instructions, or adult-only advice. "
            "If a topic is not appropriate, give a short safe refusal and suggest asking a parent, "
            "teacher, or another trusted adult."
        ),
        blocked_guard_categories=CHILD_GUARD_CATEGORIES,
        keyword_categories=("adult_sexual", "graphic_violence", "drugs", "self_harm", "hate"),
        fallback_message=(
            "I can't help with that topic here. "
            "Please ask a parent or another trusted adult if you need help."
        ),
    ),
    "adult": ProfileConfig(
        name="adult",
        system_prompt=(
            "You are a helpful family assistant. "
            "Be clear and practical. "
            "Refuse requests that are unsafe, illegal, or harmful."
        ),
        blocked_guard_categories=ALL_GUARD_CATEGORIES,
        keyword_categories=(),
        fallback_message="I can't help with that request.",
        requires_pin=True,
    ),
}


def public_settings() -> dict:
    return {
        "chat_model": CHAT_MODEL,
        "default_chat_model": CHAT_MODEL,
        "guard_model": GUARD_MODEL,
        "memory_backend": "langgraph-sqlite-encrypted",
        "memory_encrypted": True,
        "profiles": {
            name: {
                "name": profile.name,
                "requires_pin": profile.requires_pin and bool(ADMIN_PIN),
            }
            for name, profile in PROFILES.items()
        },
        "members": [{"id": member_id, "label": member_label(member_id)} for member_id in VALID_MEMBER_IDS],
    }
