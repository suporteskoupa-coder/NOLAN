from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".csv",
    ".log",
    ".ini",
    ".cfg",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".ps1",
    ".bat",
}
PDF_SUPPORTED = importlib.util.find_spec("PyPDF2") is not None


@dataclass(slots=True)
class KnowledgeSearchHit:
    title: str
    path: str
    snippet: str
    score: float


@dataclass(slots=True)
class IndexReport:
    indexed: int
    skipped: list[str]
    errors: list[str]


class KnowledgeStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def index_files(self, file_paths: list[str]) -> IndexReport:
        data = self._load()
        sources = {source["path"]: source for source in data.get("sources", [])}
        indexed = 0
        skipped: list[str] = []
        errors: list[str] = []

        for raw_path in file_paths:
            file_path = Path(raw_path)
            if not file_path.exists() or not file_path.is_file():
                skipped.append(f"{file_path.name}: arquivo indisponivel")
                continue

            try:
                extracted = self._extract_text(file_path)
            except UnsupportedFileError:
                skipped.append(f"{file_path.name}: formato nao suportado")
                continue
            except Exception as exc:
                errors.append(f"{file_path.name}: {exc}")
                continue

            if not extracted.strip():
                skipped.append(f"{file_path.name}: sem texto utilizavel")
                continue

            source = self._build_source(file_path, extracted)
            sources[str(file_path)] = source
            indexed += 1

        data["sources"] = list(sources.values())
        self._save(data)
        return IndexReport(indexed=indexed, skipped=skipped, errors=errors)

    def prompt_context(self, query: str, limit: int = 4) -> str:
        hits = self.search(query, limit=limit)
        if not hits:
            return ""
        lines = []
        for hit in hits:
            lines.append(f"- {hit.title}: {hit.snippet}")
        return "\n".join(lines)

    def search(self, query: str, limit: int = 6) -> list[KnowledgeSearchHit]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        hits: list[KnowledgeSearchHit] = []
        for source in self._load().get("sources", []):
            for chunk in source.get("chunks", []):
                chunk_tokens = set(chunk.get("tokens", []))
                overlap = len(query_tokens & chunk_tokens)
                if overlap <= 0:
                    continue
                phrase_bonus = 2.0 if query.lower() in chunk["text"].lower() else 0.0
                score = (overlap * 3.0) + phrase_bonus + min(1.5, len(chunk_tokens) / 120.0)
                hits.append(
                    KnowledgeSearchHit(
                        title=source["title"],
                        path=source["path"],
                        snippet=self._snippet(chunk["text"]),
                        score=score,
                    )
                )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:limit]

    def describe_sources(self, limit: int = 8) -> str:
        sources = self._load().get("sources", [])
        if not sources:
            return "Nenhum arquivo indexado ainda."

        ordered = sorted(sources, key=lambda source: source.get("updated_at", ""), reverse=True)
        lines = []
        for source in ordered[:limit]:
            lines.append(f"- {source['title']} ({source['kind']})")
        return "\n".join(lines)

    def dashboard_summary(self) -> str:
        sources = self._load().get("sources", [])
        if not sources:
            return "Base local vazia."

        code_count = len([source for source in sources if source.get("kind") == "codigo"])
        doc_count = len(sources) - code_count
        return (
            f"{len(sources)} fonte(s) indexada(s) | "
            f"{doc_count} documento(s) | {code_count} arquivo(s) de codigo"
        )

    def list_source_paths(self) -> list[str]:
        return [source["path"] for source in self._load().get("sources", [])]

    def clear(self) -> None:
        self._save({"sources": []})

    def _build_source(self, file_path: Path, text: str) -> dict[str, Any]:
        is_code = file_path.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".ps1", ".bat", ".css", ".html"}
        chunks = self._chunk_text(text, is_code=is_code)
        return {
            "id": hashlib.sha1(str(file_path).encode("utf-8")).hexdigest()[:12],
            "path": str(file_path),
            "title": file_path.name,
            "kind": "codigo" if is_code else "documento",
            "updated_at": file_path.stat().st_mtime_ns,
            "chunks": [
                {
                    "text": chunk,
                    "tokens": sorted(self._tokenize(chunk)),
                }
                for chunk in chunks
            ],
        }

    def _extract_text(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix in TEXT_EXTENSIONS:
            return file_path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".pdf" and PDF_SUPPORTED:
            from PyPDF2 import PdfReader  # type: ignore

            reader = PdfReader(str(file_path))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            return "\n".join(pages)

        raise UnsupportedFileError(str(file_path))

    def _chunk_text(self, text: str, is_code: bool) -> list[str]:
        cleaned = text.replace("\r", "")
        if is_code:
            lines = cleaned.splitlines()
            chunks: list[str] = []
            current: list[str] = []
            for line in lines:
                current.append(line)
                if len(current) >= 28 or sum(len(item) for item in current) >= 1200:
                    chunks.append("\n".join(current).strip())
                    current = []
            if current:
                chunks.append("\n".join(current).strip())
            return [chunk for chunk in chunks if chunk]

        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", cleaned) if paragraph.strip()]
        chunks = []
        current = ""
        for paragraph in paragraphs:
            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if len(candidate) > 900 and current:
                chunks.append(current.strip())
                current = paragraph
            else:
                current = candidate
        if current.strip():
            chunks.append(current.strip())
        if not chunks and cleaned.strip():
            chunks.append(cleaned.strip())
        return chunks

    def _snippet(self, text: str, max_length: int = 220) -> str:
        collapsed = re.sub(r"\s+", " ", text).strip()
        if len(collapsed) <= max_length:
            return collapsed
        return collapsed[: max_length - 3].rstrip() + "..."

    def _tokenize(self, text: str) -> set[str]:
        return {token.lower() for token in TOKEN_RE.findall(text)}

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"sources": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"sources": []}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class UnsupportedFileError(Exception):
    pass
