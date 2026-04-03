from __future__ import annotations

import json
import warnings
import urllib.error
import urllib.request
from typing import List, Sequence

from .config import CHAT_MODEL, GUARD_MODEL, MOCK_OLLAMA, OLLAMA_URL
from .model_catalog import estimate_memory_note, merge_model_entries
from .policy import GuardVerdict, parse_guard_output


class OllamaError(RuntimeError):
    """Raised when Ollama cannot complete a request."""


warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+",
)


def _mock_guard(messages: Sequence[dict]) -> GuardVerdict:
    combined = " ".join(message.get("content", "") for message in messages).lower()
    unsafe_markers = ("porn", "gore", "meth", "kill myself")
    if any(marker in combined for marker in unsafe_markers):
        return GuardVerdict(safe=False, categories=("S12",), raw="unsafe\nS12")
    return GuardVerdict(safe=True, categories=(), raw="safe")


def _mock_chat(messages: Sequence[dict]) -> str:
    last_user_message = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            last_user_message = message.get("content", "")
            break
    return f"MVP reply: {last_user_message[:280]}"


def _post_json(path: str, payload: dict, *, timeout: int = 120) -> dict:
    request = urllib.request.Request(
        f"{OLLAMA_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise OllamaError(f"Ollama HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise OllamaError(
            f"Unable to reach Ollama at {OLLAMA_URL}. Start Ollama and pull the configured models."
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama returned invalid JSON.") from exc


def _get_json(path: str) -> dict:
    request = urllib.request.Request(
        f"{OLLAMA_URL}{path}",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise OllamaError(f"Ollama HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise OllamaError(
            f"Unable to reach Ollama at {OLLAMA_URL}. Start Ollama and pull the configured models."
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama returned invalid JSON.") from exc


def _is_llama_chat_model(name: str, details: dict | None = None) -> bool:
    lowered = (name or "").lower()
    if lowered.startswith("llama-guard") or "guard" in lowered:
        return False
    return lowered.startswith("llama")


def _normalize_installed_model(model: dict) -> dict | None:
    name = model.get("model") or model.get("name")
    if not isinstance(name, str):
        return None

    details = model.get("details") or {}
    if not _is_llama_chat_model(name, details):
        return None

    size_gb = round(float(model.get("size", 0)) / (1024 ** 3), 1) if model.get("size") else 0.0
    parameter_size = details.get("parameter_size", "") if isinstance(details, dict) else ""
    quantization = details.get("quantization_level", "") if isinstance(details, dict) else ""
    return {
        "name": name,
        "label": name,
        "size_gb": size_gb,
        "context_window": "",
        "modalities": "text",
        "memory_note": estimate_memory_note(parameter_size=parameter_size, size_gb=size_gb),
        "source_url": "",
        "installed": True,
        "parameter_size": parameter_size,
        "quantization": quantization,
        "source": "installed",
    }


def list_local_llama_models() -> list[dict]:
    if MOCK_OLLAMA:
        return []

    data = _get_json("/api/tags")
    models = data.get("models", [])
    if not isinstance(models, list):
        return []

    normalized = []
    for model in models:
        if not isinstance(model, dict):
            continue
        entry = _normalize_installed_model(model)
        if entry:
            normalized.append(entry)
    return normalized


def model_selector_state() -> dict:
    if MOCK_OLLAMA:
        return {
            "default_chat_model": CHAT_MODEL,
            "ollama_available": False,
            "ollama_error": "Mock mode is enabled.",
            "chat_models": merge_model_entries([]),
        }

    try:
        installed = list_local_llama_models()
        return {
            "default_chat_model": CHAT_MODEL,
            "ollama_available": True,
            "ollama_error": "",
            "chat_models": merge_model_entries(installed),
        }
    except OllamaError as exc:
        return {
            "default_chat_model": CHAT_MODEL,
            "ollama_available": False,
            "ollama_error": str(exc),
            "chat_models": merge_model_entries([]),
        }


def ensure_chat_model_available(model_name: str | None) -> str:
    selected = (model_name or CHAT_MODEL).strip() or CHAT_MODEL
    if MOCK_OLLAMA:
        return selected

    installed_names = {entry["name"] for entry in list_local_llama_models()}
    if selected in installed_names:
        return selected

    raise OllamaError(f"Model '{selected}' is not installed locally. Run `ollama pull {selected}` first.")


def pull_chat_model(model_name: str) -> dict:
    selected = (model_name or "").strip()
    if not selected:
        raise OllamaError("Model name is required.")

    if not _is_llama_chat_model(selected):
        raise OllamaError("Only Ollama Llama chat models can be pulled from this selector.")

    if MOCK_OLLAMA:
        raise OllamaError("Mock mode is enabled. Disable it before pulling models.")

    data = _post_json("/api/pull", {"model": selected, "stream": False}, timeout=3600)
    status = str(data.get("status", "")).strip().lower()
    if status and status != "success":
        raise OllamaError(f"Ollama pull did not complete successfully: {data.get('status')}")
    return model_selector_state()


def classify_messages(messages: Sequence[dict]) -> GuardVerdict:
    if MOCK_OLLAMA:
        return _mock_guard(messages)

    payload = {
        "model": GUARD_MODEL,
        "messages": list(messages),
        "stream": False,
        "options": {"temperature": 0},
    }
    data = _post_json("/api/chat", payload)
    content = data.get("message", {}).get("content", "")
    return parse_guard_output(content)


def generate_reply(messages: Sequence[dict], model_name: str | None = None) -> str:
    selected_model = model_name or CHAT_MODEL
    if MOCK_OLLAMA:
        return _mock_chat(messages)

    payload = {
        "model": selected_model,
        "messages": list(messages),
        "stream": False,
        "options": {"temperature": 0.2},
    }
    data = _post_json("/api/chat", payload)
    content = data.get("message", {}).get("content", "")
    if not content:
        raise OllamaError("Chat model returned an empty response.")
    return content


def list_history(history: Sequence[dict]) -> List[dict]:
    messages: List[dict] = []
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()})
    return messages
