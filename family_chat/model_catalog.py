from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Optional


@dataclass(frozen=True)
class LlamaCatalogEntry:
    name: str
    label: str
    size_gb: float
    context_window: str
    modalities: str
    memory_note: str
    source_url: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["installed"] = False
        data["parameter_size"] = ""
        data["quantization"] = ""
        data["source"] = "catalog"
        return data


OFFICIAL_LLAMA_CATALOG = (
    LlamaCatalogEntry(
        name="llama3.2:1b",
        label="Llama 3.2 1B",
        size_gb=1.3,
        context_window="128K",
        modalities="text",
        memory_note="Approx 4 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama3.2",
    ),
    LlamaCatalogEntry(
        name="llama3.2:3b",
        label="Llama 3.2 3B",
        size_gb=2.0,
        context_window="128K",
        modalities="text",
        memory_note="Approx 6 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama3.2",
    ),
    LlamaCatalogEntry(
        name="llama3:8b",
        label="Llama 3 8B",
        size_gb=4.7,
        context_window="8K",
        modalities="text",
        memory_note="Approx 8 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama3",
    ),
    LlamaCatalogEntry(
        name="llama3.1:8b",
        label="Llama 3.1 8B",
        size_gb=4.9,
        context_window="128K",
        modalities="text",
        memory_note="Approx 8 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama3.1",
    ),
    LlamaCatalogEntry(
        name="llama2:7b",
        label="Llama 2 7B",
        size_gb=3.8,
        context_window="4K",
        modalities="text",
        memory_note="Approx 8 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama2",
    ),
    LlamaCatalogEntry(
        name="llama2:13b",
        label="Llama 2 13B",
        size_gb=7.4,
        context_window="4K",
        modalities="text",
        memory_note="Approx 16 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama2",
    ),
    LlamaCatalogEntry(
        name="llama3:70b",
        label="Llama 3 70B",
        size_gb=40.0,
        context_window="8K",
        modalities="text",
        memory_note="Approx 64 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama3",
    ),
    LlamaCatalogEntry(
        name="llama3.1:70b",
        label="Llama 3.1 70B",
        size_gb=43.0,
        context_window="128K",
        modalities="text",
        memory_note="Approx 64 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama3.1",
    ),
    LlamaCatalogEntry(
        name="llama3.3:70b",
        label="Llama 3.3 70B",
        size_gb=43.0,
        context_window="128K",
        modalities="text",
        memory_note="Approx 64 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama3.3",
    ),
    LlamaCatalogEntry(
        name="llama4:16x17b",
        label="Llama 4 Scout (16x17B)",
        size_gb=67.0,
        context_window="10M",
        modalities="text,image",
        memory_note="Approx 80 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama4",
    ),
    LlamaCatalogEntry(
        name="llama3.1:405b",
        label="Llama 3.1 405B",
        size_gb=243.0,
        context_window="128K",
        modalities="text",
        memory_note="Approx 256 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama3.1",
    ),
    LlamaCatalogEntry(
        name="llama4:128x17b",
        label="Llama 4 Maverick (128x17B)",
        size_gb=245.0,
        context_window="1M",
        modalities="text,image",
        memory_note="Approx 256 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama4",
    ),
    LlamaCatalogEntry(
        name="llama2:70b",
        label="Llama 2 70B",
        size_gb=39.0,
        context_window="4K",
        modalities="text",
        memory_note="Approx 64 GB+ unified/GPU memory",
        source_url="https://ollama.com/library/llama2",
    ),
)


CATALOG_BY_NAME = {entry.name: entry for entry in OFFICIAL_LLAMA_CATALOG}


def parse_parameter_size(value: str) -> Optional[float]:
    raw = (value or "").strip().upper()
    if not raw.endswith("B"):
        return None
    try:
        return float(raw[:-1])
    except ValueError:
        return None


def estimate_memory_note(*, parameter_size: str = "", size_gb: float = 0.0) -> str:
    params = parse_parameter_size(parameter_size)
    if params is not None:
        if params <= 1.5:
            return "Approx 4 GB+ unified/GPU memory"
        if params <= 3.5:
            return "Approx 6 GB+ unified/GPU memory"
        if params <= 8.5:
            return "Approx 8 GB+ unified/GPU memory"
        if params <= 14:
            return "Approx 16 GB+ unified/GPU memory"
        if params <= 35:
            return "Approx 24-32 GB+ unified/GPU memory"
        if params <= 80:
            return "Approx 64 GB+ unified/GPU memory"
        if params <= 150:
            return "Approx 80-128 GB+ unified/GPU memory"
        return "Approx 256 GB+ unified/GPU memory"

    if size_gb <= 2.0:
        return "Approx 4 GB+ unified/GPU memory"
    if size_gb <= 3.0:
        return "Approx 6 GB+ unified/GPU memory"
    if size_gb <= 5.5:
        return "Approx 8 GB+ unified/GPU memory"
    if size_gb <= 8.0:
        return "Approx 16 GB+ unified/GPU memory"
    if size_gb <= 18.0:
        return "Approx 24-32 GB+ unified/GPU memory"
    if size_gb <= 50.0:
        return "Approx 64 GB+ unified/GPU memory"
    if size_gb <= 90.0:
        return "Approx 80-128 GB+ unified/GPU memory"
    return "Approx 256 GB+ unified/GPU memory"


def llama_catalog_names() -> set[str]:
    return set(CATALOG_BY_NAME)


def catalog_dicts() -> list[dict]:
    return [entry.to_dict() for entry in OFFICIAL_LLAMA_CATALOG]


def find_catalog_entry(name: str) -> Optional[LlamaCatalogEntry]:
    return CATALOG_BY_NAME.get(name)


def merge_model_entries(installed_entries: Iterable[dict]) -> list[dict]:
    merged = {entry.name: entry.to_dict() for entry in OFFICIAL_LLAMA_CATALOG}

    for entry in installed_entries:
        name = entry["name"]
        if name in merged:
            merged[name]["installed"] = entry.get("installed", True)
            merged[name]["parameter_size"] = entry.get("parameter_size", "")
            merged[name]["quantization"] = entry.get("quantization", "")
            if entry.get("size_gb"):
                merged[name]["size_gb"] = entry["size_gb"]
            if entry.get("memory_note"):
                merged[name]["memory_note"] = entry["memory_note"]
            merged[name]["source"] = "catalog+installed"
        else:
            merged[name] = entry

    ordered_names = [entry.name for entry in OFFICIAL_LLAMA_CATALOG]
    extra_names = sorted(name for name in merged if name not in ordered_names)
    return [merged[name] for name in ordered_names if name in merged] + [merged[name] for name in extra_names]
