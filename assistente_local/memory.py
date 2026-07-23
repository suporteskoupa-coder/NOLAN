from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")


@dataclass(slots=True)
class MemoryEntry:
    role: str
    speaker: str
    content: str
    timestamp: str
    importance: int = 1
    tags: list[str] = field(default_factory=list)


class MemoryStore:
    def __init__(self, path: Path, limit: int = 12) -> None:
        self.path = path
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[MemoryEntry]:
        if not self.path.exists():
            return []

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            entries: list[MemoryEntry] = []
            for item in raw:
                entries.append(
                    MemoryEntry(
                        role=item["role"],
                        speaker=item["speaker"],
                        content=item["content"],
                        timestamp=item["timestamp"],
                        importance=int(item.get("importance", 1)),
                        tags=list(item.get("tags", [])),
                    )
                )
            return entries
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            return []

    def add(
        self,
        role: str,
        speaker: str,
        content: str,
        importance: int | None = None,
        tags: list[str] | None = None,
    ) -> None:
        entries = self.load()
        inferred_tags = tags or self._infer_tags(content)
        inferred_importance = importance if importance is not None else self._score_importance(role, content, inferred_tags)
        entries.append(
            MemoryEntry(
                role=role,
                speaker=speaker,
                content=content,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                importance=max(1, min(5, int(inferred_importance))),
                tags=inferred_tags,
            )
        )
        entries = self._prune(entries)
        self._save_entries(entries)

    def as_context_block(self) -> str:
        entries = [entry for entry in self.load() if self._include_in_prompt(entry)]
        if not entries:
            return "Sem memoria registrada ainda."

        recent_entries = entries[-6:]
        important_entries = [
            entry
            for entry in entries[:-6]
            if entry.importance >= 4 and self._include_in_prompt(entry)
        ]
        important_entries.sort(key=lambda entry: (entry.importance, entry.timestamp), reverse=True)
        selected = self._dedupe_entries(important_entries[:3] + recent_entries)
        if not selected:
            return "Sem memoria conversacional relevante ainda."

        lines = [self._format_entry(entry) for entry in selected]
        return "\n".join(lines)

    def important_context(self, limit: int = 4) -> str:
        entries = [entry for entry in self.load() if self._include_in_prompt(entry)]
        important = [entry for entry in entries if entry.importance >= 4]
        important.sort(key=lambda entry: (entry.importance, entry.timestamp), reverse=True)
        if not important:
            return ""
        lines = [self._format_entry(entry) for entry in important[:limit]]
        return "\n".join(lines)

    def semantic_recall(self, query: str, limit: int = 4) -> list[str]:
        entries = [entry for entry in self.load() if self._include_in_prompt(entry)]
        if not entries:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, str]] = []
        total_entries = len(entries)
        for index, entry in enumerate(entries):
            content_tokens = self._tokenize(entry.content)
            overlap = len(query_tokens & content_tokens)
            if overlap <= 0:
                continue
            recency_bonus = (index + 1) / max(total_entries, 1)
            score = (overlap * 5) + (entry.importance * 1.5) + recency_bonus
            scored.append((score, self._format_entry(entry)))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [content for _, content in scored[:limit]]

    def timeline_report(self) -> str:
        entries = self.load()
        if not entries:
            return "Sem linha do tempo ainda."

        recent = entries[-3:]
        lines = []
        for entry in recent:
            lines.append(f"- {entry.timestamp}: {entry.speaker} registrou algo com importancia {entry.importance}.")
        return "\n".join(lines)

    def memory_posture(self) -> str:
        entries = self.load()
        important = len([entry for entry in entries if entry.importance >= 4])
        if important >= 8:
            return "profunda"
        if important >= 4:
            return "adaptativa"
        return "recente"

    def clear(self) -> None:
        self._save_entries([])

    def _format_entry(self, entry: MemoryEntry) -> str:
        return f"[{entry.timestamp}] {entry.speaker}: {entry.content}"

    def _include_in_prompt(self, entry: MemoryEntry) -> bool:
        normalized = entry.content.lower()
        blocked_fragments = (
            "diagnostico do jarvis v2",
            "memoria persistente",
            "estado interno",
            "automacao segura",
            "ollama:",
            "modo seguro ativo",
            "nao consegui consultar o modelo local agora",
            "\\memoria.json",
            "\\estado.json",
            "sistema iniciado",
            "jarvis v2 aguardando sua chamada",
        )
        return not any(fragment in normalized for fragment in blocked_fragments)

    def _score_importance(self, role: str, content: str, tags: list[str]) -> int:
        normalized = content.lower()
        score = 1
        if role == "user":
            score += 1
        if len(content) >= 80:
            score += 1
        if any(tag in {"profile", "preference", "reasoning", "belief"} for tag in tags):
            score += 2
        if any(token in normalized for token in ("importante", "lembre", "meu nome", "eu gosto", "eu prefiro")):
            score += 1
        if "?" in content and any(token in normalized for token in ("sobre mim", "acha de mim", "lembra")):
            score += 1
        return max(1, min(5, score))

    def _infer_tags(self, content: str) -> list[str]:
        normalized = content.lower()
        tags: list[str] = []
        if any(token in normalized for token in ("meu nome", "me chamo", "pode me chamar")):
            tags.append("profile")
        if any(token in normalized for token in ("eu gosto", "eu prefiro", "eu nao gosto", "eu odeio")):
            tags.append("preference")
        if "=" in content or any(token in normalized for token in ("equivale", "relacao", "raciocine")):
            tags.append("reasoning")
        if any(token in normalized for token in ("sobre mim", "acredita sobre mim", "hipotese")):
            tags.append("belief")
        if any(token in normalized for token in ("abrir", "comando", "programa", "calendario")):
            tags.append("action")
        if any(token in normalized for token in ("voz", "audio", "fale", "falar")):
            tags.append("voice")
        if not tags:
            tags.append("general")
        return tags

    def _prune(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        if len(entries) <= self.limit + 6:
            return entries

        recent = entries[-self.limit :]
        preserved = [
            entry
            for entry in entries[:-self.limit]
            if entry.importance >= 4 and self._include_in_prompt(entry)
        ]
        preserved.sort(key=lambda entry: (entry.importance, entry.timestamp), reverse=True)
        selected = self._dedupe_entries(preserved[:6] + recent)
        selected.sort(key=lambda entry: entry.timestamp)
        return selected

    def _dedupe_entries(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[MemoryEntry] = []
        for entry in entries:
            key = (entry.timestamp, entry.speaker, entry.content)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(entry)
        deduped.sort(key=lambda entry: entry.timestamp)
        return deduped

    def _tokenize(self, text: str) -> set[str]:
        return {token.lower() for token in TOKEN_RE.findall(text)}

    def _save_entries(self, entries: list[MemoryEntry]) -> None:
        payload: list[dict[str, Any]] = [
            {
                "role": entry.role,
                "speaker": entry.speaker,
                "content": entry.content,
                "timestamp": entry.timestamp,
                "importance": entry.importance,
                "tags": entry.tags,
            }
            for entry in entries
        ]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
