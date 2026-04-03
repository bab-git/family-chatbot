from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph


class MemoryConfigurationError(RuntimeError):
    """Raised when encrypted memory is not configured correctly."""


def _persist_turn(_: MessagesState) -> dict:
    return {}


def _message_role(message: BaseMessage) -> Optional[str]:
    role_map = {
        "human": "user",
        "ai": "assistant",
        "system": "system",
    }
    return role_map.get(message.type)


def _clip_text(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "..."


class LangGraphMemoryStore:
    def __init__(self, db_path: Path, aes_key: str) -> None:
        if len(aes_key.encode("utf-8")) not in (16, 24, 32):
            raise MemoryConfigurationError(
                "LANGGRAPH_AES_KEY must be exactly 16, 24, or 32 bytes long."
            )

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._connection = sqlite3.connect(str(db_path), check_same_thread=False)
        serializer = EncryptedSerializer.from_pycryptodome_aes(key=aes_key.encode("utf-8"))
        self._checkpointer = SqliteSaver(self._connection, serde=serializer)
        self._checkpointer.setup()

        builder = StateGraph(MessagesState)
        builder.add_node("persist_turn", _persist_turn)
        builder.add_edge(START, "persist_turn")
        builder.add_edge("persist_turn", END)
        self._graph = builder.compile(checkpointer=self._checkpointer)

    @staticmethod
    def build_thread_id(member_id: str, profile_name: str, conversation_id: str | None = None) -> str:
        if not conversation_id or conversation_id == "default":
            return f"family::{member_id}::{profile_name}"
        return f"family::{member_id}::{profile_name}::{conversation_id}"

    @staticmethod
    def conversation_id_from_thread_id(
        member_id: str, profile_name: str, thread_id: str
    ) -> str | None:
        base_thread_id = LangGraphMemoryStore.build_thread_id(member_id, profile_name, "default")
        if thread_id == base_thread_id:
            return "default"

        prefix = base_thread_id + "::"
        if thread_id.startswith(prefix):
            return thread_id[len(prefix) :]
        return None

    def load_messages(
        self,
        member_id: str,
        profile_name: str,
        conversation_id: str | None = None,
        *,
        limit: Optional[int] = None,
    ) -> List[dict]:
        config = {
            "configurable": {
                "thread_id": self.build_thread_id(member_id, profile_name, conversation_id),
            }
        }
        snapshot = self._graph.get_state(config)
        values = snapshot.values if snapshot else {}
        messages = values.get("messages", []) if isinstance(values, dict) else []

        history: List[dict] = []
        for message in messages:
            if not isinstance(message, BaseMessage):
                continue

            role = _message_role(message)
            if role not in {"user", "assistant"}:
                continue

            content = message.content
            if isinstance(content, str) and content.strip():
                history.append({"role": role, "content": content.strip()})

        if limit is not None and limit > 0:
            return history[-limit:]
        return history

    def append_turn(
        self,
        member_id: str,
        profile_name: str,
        conversation_id: str | None = None,
        *,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        config = {
            "configurable": {
                "thread_id": self.build_thread_id(member_id, profile_name, conversation_id),
            }
        }
        self._graph.invoke(
            {
                "messages": [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_reply},
                ]
            },
            config,
        )

    def list_conversations(
        self,
        member_id: str,
        profile_name: str,
        *,
        limit: int = 20,
    ) -> List[dict]:
        base_thread_id = self.build_thread_id(member_id, profile_name, "default")
        query = """
            SELECT thread_id, MAX(checkpoint_id) AS latest_checkpoint_id
            FROM checkpoints
            WHERE thread_id = ? OR thread_id LIKE ?
            GROUP BY thread_id
            ORDER BY latest_checkpoint_id DESC
            LIMIT ?
        """

        with self._connection:
            rows = self._connection.execute(
                query,
                (base_thread_id, f"{base_thread_id}::%", max(limit, 1)),
            ).fetchall()

        conversations: List[dict] = []
        for thread_id, latest_checkpoint_id in rows:
            conversation_id = self.conversation_id_from_thread_id(member_id, profile_name, thread_id)
            if conversation_id is None:
                continue

            messages = self.load_messages(member_id, profile_name, conversation_id)
            if not messages:
                continue

            title = "New chat"
            for message in messages:
                if message["role"] == "user":
                    title = _clip_text(message["content"], 48)
                    break

            preview_source = messages[-1]["content"]
            conversations.append(
                {
                    "conversation_id": conversation_id,
                    "title": title,
                    "preview": _clip_text(preview_source, 84),
                    "message_count": len(messages),
                    "is_default": conversation_id == "default",
                    "sort_key": latest_checkpoint_id,
                }
            )

        return conversations

    def close(self) -> None:
        self._connection.close()
