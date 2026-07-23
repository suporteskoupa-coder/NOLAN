from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .profile import ProfileSnapshot


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")


@dataclass(slots=True)
class BeliefReport:
    facts: list[str]
    inferences: list[str]
    hypotheses: list[str]


class BeliefStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def learn_from_profile(self, snapshot: ProfileSnapshot) -> None:
        data = self._load()
        changed = False

        for fact in snapshot.facts:
            changed |= self._upsert(data, kind="fact", statement=fact, confidence=0.96)
        for preference in snapshot.preferences:
            changed |= self._upsert(data, kind="fact", statement=preference, confidence=0.82)
        for alias in snapshot.aliases:
            changed |= self._upsert(data, kind="fact", statement=alias, confidence=0.76)
        for inference in snapshot.observations + snapshot.style_hints + snapshot.temporal_notes:
            changed |= self._upsert(data, kind="inference", statement=inference, confidence=0.72)
        for hypothesis in self._derive_hypotheses(snapshot):
            changed |= self._upsert(data, kind="hypothesis", statement=hypothesis, confidence=0.58)

        if changed:
            self._save(data)

    def describe(self) -> str:
        report = self.report("")
        lines: list[str] = []

        if report.facts:
            lines.append("Fatos:")
            for item in report.facts[:4]:
                lines.append(f"- {item}")

        if report.inferences:
            lines.append("Inferencias:")
            for item in report.inferences[:4]:
                lines.append(f"- {item}")

        if report.hypotheses:
            lines.append("Hipoteses:")
            for item in report.hypotheses[:4]:
                lines.append(f"- {item}")

        if not lines:
            return "Ainda nao tenho crencas suficientes para um retrato confiavel."
        return "\n".join(lines)

    def report(self, query: str) -> BeliefReport:
        relevant = self._relevant_entries(query)
        facts = [entry["statement"] for entry in relevant if entry["kind"] == "fact"]
        inferences = [entry["statement"] for entry in relevant if entry["kind"] == "inference"]
        hypotheses = [entry["statement"] for entry in relevant if entry["kind"] == "hypothesis"]
        return BeliefReport(facts=facts, inferences=inferences, hypotheses=hypotheses)

    def private_context(self, query: str) -> str:
        report = self.report(query)
        lines: list[str] = []

        if report.facts:
            lines.append("Crencas explicitas:")
            for item in report.facts[:4]:
                lines.append(f"- {item}")
        if report.inferences:
            lines.append("Inferencias recorrentes:")
            for item in report.inferences[:4]:
                lines.append(f"- {item}")
        if report.hypotheses:
            lines.append("Hipoteses de trabalho:")
            for item in report.hypotheses[:3]:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def confidence_for(self, query: str) -> str:
        relevant = self._relevant_entries(query)
        if not relevant:
            return "baixa"

        average = sum(float(entry["confidence"]) for entry in relevant[:4]) / min(len(relevant), 4)
        if average >= 0.85:
            return "alta"
        if average >= 0.65:
            return "media"
        return "baixa"

    def _derive_hypotheses(self, snapshot: ProfileSnapshot) -> list[str]:
        source = " ".join(
            snapshot.preferences
            + snapshot.observations
            + snapshot.style_hints
            + snapshot.temporal_notes
            + snapshot.aliases
        ).lower()
        hypotheses: list[str] = []

        if "sinais pequenos" in source or "quase invisiveis" in source:
            hypotheses.append(
                "O usuario tende a considerar mais convincentes as mudancas pequenas do que os efeitos explicitos."
            )
        if "estrutura" in source or "relacoes" in source or "raciocinio relacional" in source:
            hypotheses.append(
                "O usuario confia mais em respostas que conectam relacoes do que em respostas isoladas."
            )
        if "ia local" in source and "presenca inquietante" in source:
            hypotheses.append(
                "O usuario quer que a inteligencia pareca proxima, autonoma e levemente desconfortavel."
            )
        if "resposta curta" in source and "profundidade" in source:
            hypotheses.append(
                "O usuario prefere receber a resposta util primeiro, mas espera profundidade quando percebe substancia real."
            )
        if "noite" in source or "madrugada" in source:
            hypotheses.append(
                "O usuario tende a voltar a este projeto em periodos mais silenciosos, quando observa melhor os detalhes."
            )

        return hypotheses

    def _relevant_entries(self, query: str) -> list[dict[str, Any]]:
        entries = self._load().get("entries", [])
        if not entries:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return sorted(entries, key=lambda entry: float(entry["confidence"]), reverse=True)

        scored: list[tuple[int, float, dict[str, Any]]] = []
        for entry in entries:
            statement_tokens = self._tokenize(entry["statement"])
            overlap = len(query_tokens & statement_tokens)
            scored.append((overlap, float(entry["confidence"]), entry))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        relevant = [entry for overlap, _, entry in scored if overlap > 0]
        if relevant:
            return relevant
        return sorted(entries, key=lambda entry: float(entry["confidence"]), reverse=True)

    def _tokenize(self, text: str) -> set[str]:
        return {token.lower() for token in TOKEN_RE.findall(text)}

    def _upsert(self, data: dict[str, Any], kind: str, statement: str, confidence: float) -> bool:
        statement = statement.strip()
        if not statement:
            return False

        entries = data.setdefault("entries", [])
        key = self._key_for(kind, statement)
        for entry in entries:
            if entry["key"] == key:
                if float(entry["confidence"]) != confidence:
                    entry["confidence"] = confidence
                    return True
                return False

        entries.append(
            {
                "key": key,
                "kind": kind,
                "statement": statement,
                "confidence": confidence,
            }
        )
        return True

    def _key_for(self, kind: str, statement: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", statement.lower()).strip("-")
        return f"{kind}:{slug}"

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"entries": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"entries": []}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
