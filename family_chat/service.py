from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Sequence

from .config import (
    ADMIN_PIN,
    CONVERSATION_LIST_LIMIT,
    HISTORY_LOAD_LIMIT,
    MEMORY_CONTEXT_LIMIT,
    PROFILES,
    VALID_MEMBER_IDS,
)
from .memory import LangGraphMemoryStore
from .ollama_client import classify_messages, ensure_chat_model_available, generate_reply
from .policy import GuardVerdict, evaluate_text_for_profile


@dataclass(frozen=True)
class ChatResult:
    blocked: bool
    reply: str
    reason: str = ""
    categories: Sequence[str] = ()


class ChatService:
    def __init__(
        self,
        memory_store: LangGraphMemoryStore,
        *,
        classify: Callable[[Sequence[dict]], GuardVerdict] = classify_messages,
        generate: Callable[..., str] = generate_reply,
        resolve_model: Callable[[str | None], str] = ensure_chat_model_available,
    ) -> None:
        self._memory_store = memory_store
        self._classify = classify
        self._generate = generate
        self._resolve_model = resolve_model

    def list_history(
        self,
        *,
        profile_name: str,
        member_id: str,
        pin: str = "",
        conversation_id: str | None = None,
    ) -> list[dict]:
        self._validate_access(profile_name=profile_name, member_id=member_id, pin=pin)
        conversation_id = self._normalize_conversation_id(conversation_id)
        return self._memory_store.load_messages(
            member_id,
            profile_name,
            conversation_id,
            limit=HISTORY_LOAD_LIMIT,
        )

    def list_conversations(
        self,
        *,
        profile_name: str,
        member_id: str,
        pin: str = "",
    ) -> list[dict]:
        self._validate_access(profile_name=profile_name, member_id=member_id, pin=pin)
        conversations = self._memory_store.list_conversations(
            member_id,
            profile_name,
            limit=CONVERSATION_LIST_LIMIT,
        )
        return [
            {
                "conversation_id": item["conversation_id"],
                "title": item["title"],
                "preview": item["preview"],
                "message_count": item["message_count"],
                "is_default": item["is_default"],
            }
            for item in conversations
        ]

    def chat(
        self,
        *,
        profile_name: str,
        member_id: str,
        pin: str = "",
        user_message: str,
        chat_model: str | None = None,
        conversation_id: str | None = None,
    ) -> ChatResult:
        profile = self._validate_access(profile_name=profile_name, member_id=member_id, pin=pin)
        selected_model = self._resolve_model(chat_model)
        normalized_conversation_id = self._normalize_conversation_id(conversation_id)

        input_verdict = self._classify([{"role": "user", "content": user_message}])
        input_decision = evaluate_text_for_profile(profile, user_message, input_verdict)
        if not input_decision.allowed:
            return ChatResult(
                blocked=True,
                reply=profile.fallback_message,
                reason=input_decision.reason,
                categories=tuple(input_decision.categories),
            )

        history = self._memory_store.load_messages(
            member_id,
            profile_name,
            normalized_conversation_id,
            limit=MEMORY_CONTEXT_LIMIT,
        )
        prompt_messages = [{"role": "system", "content": profile.system_prompt}]
        prompt_messages.extend(history)
        prompt_messages.append({"role": "user", "content": user_message})

        reply = self._generate(prompt_messages, selected_model)
        output_verdict = self._classify(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply},
            ]
        )
        output_decision = evaluate_text_for_profile(profile, reply, output_verdict)
        if not output_decision.allowed:
            return ChatResult(
                blocked=True,
                reply=profile.fallback_message,
                reason=output_decision.reason,
                categories=tuple(output_decision.categories),
            )

        self._memory_store.append_turn(
            member_id,
            profile_name,
            normalized_conversation_id,
            user_message=user_message,
            assistant_reply=reply,
        )
        return ChatResult(blocked=False, reply=reply)

    @staticmethod
    def _validate_access(*, profile_name: str, member_id: str, pin: str):
        profile = PROFILES.get(profile_name)
        if not profile:
            raise ValueError("Unknown profile.")

        if member_id not in VALID_MEMBER_IDS:
            raise ValueError("Unknown family member.")

        if profile.requires_pin:
            if not ADMIN_PIN:
                raise PermissionError("Adult profile is disabled until FAMILY_CHAT_ADMIN_PIN is configured.")
            if pin != ADMIN_PIN:
                raise PermissionError("Adult profile requires the correct PIN.")

        return profile

    @staticmethod
    def _normalize_conversation_id(conversation_id: str | None) -> str:
        if not conversation_id:
            return "default"

        normalized = conversation_id.strip().lower()
        if not normalized:
            return "default"

        if len(normalized) > 120:
            raise ValueError("Conversation id is too long.")

        if not re.fullmatch(r"[a-z0-9_-]+", normalized):
            raise ValueError("Conversation id contains invalid characters.")

        return normalized
