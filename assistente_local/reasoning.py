from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EQUATION_RE = re.compile(r"([A-Za-z0-9_+\-*/() ]+?)\s*=\s*([A-Za-z0-9_+\-*/() ]+)")
OPERATION_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*([+*])\s*([A-Za-z0-9_]+)\s*$")


@dataclass(slots=True)
class ReasoningResult:
    handled: bool
    answer: str = ""
    note: str = ""


class ReasoningStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def learn_from_text(self, text: str) -> None:
        if "?" in text:
            return

        equations = self._extract_equations(text)
        if not equations:
            return

        data = self._load()
        changed = False
        for left, right in equations:
            changed |= self._link(data, left, right)

        if changed:
            self._save(data)

    def answer_query(self, text: str) -> ReasoningResult:
        inline_answer = self._answer_inline_equation_question(text)
        if inline_answer.handled:
            return inline_answer

        stored_equation_answer = self._answer_known_equation_question(text)
        if stored_equation_answer.handled:
            return stored_equation_answer

        symbol = self._extract_symbol_query(text)
        if not symbol:
            return ReasoningResult(handled=False)

        data = self._load()
        related = self._related_expressions(data, symbol)
        if not related:
            return ReasoningResult(handled=False)

        preferred = related[0]
        symbol_display = self._preferred_display(data, symbol)

        if self._looks_like_origin_question(text):
            return ReasoningResult(
                handled=True,
                answer=f"Se mantivermos a relacao registrada, {symbol_display} vem de {preferred}.",
            )

        return ReasoningResult(
            handled=True,
            answer=f"Pela relacao registrada, {symbol_display} = {preferred}.",
        )

    def relevant_context(self, text: str) -> str:
        data = self._load()
        symbols = self._extract_symbols(text)
        notes: list[str] = []

        for symbol in symbols:
            related = self._related_expressions(data, symbol)
            if not related:
                continue
            notes.append(f"{self._preferred_display(data, symbol)} = {related[0]}")
            if len(notes) == 3:
                break

        if not notes:
            return ""
        return "\n".join(f"- {note}" for note in notes)

    def _answer_inline_equation_question(self, text: str) -> ReasoningResult:
        equations = self._extract_equations(text)
        if len(equations) < 2:
            return ReasoningResult(handled=False)

        first_left, first_right = equations[0]
        second_left, second_right = equations[1]

        first_a = self._canonical_expression(first_left)
        first_b = self._canonical_expression(first_right)
        second_a = self._canonical_expression(second_left)
        second_b = self._canonical_expression(second_right)

        same_order = first_a == second_a and first_b == second_b
        reverse_order = first_a == second_b and first_b == second_a

        if same_order or reverse_order:
            return ReasoningResult(
                handled=True,
                answer=(
                    "Sim. Se mantivermos essa igualdade, a relacao continua valida nos dois sentidos."
                ),
            )

        return ReasoningResult(handled=False)

    def _answer_known_equation_question(self, text: str) -> ReasoningResult:
        if "?" not in text:
            return ReasoningResult(handled=False)

        equations = self._extract_equations(text)
        if len(equations) != 1:
            return ReasoningResult(handled=False)

        left, right = equations[0]
        data = self._load()
        if self._are_equivalent(data, left, right):
            return ReasoningResult(
                handled=True,
                answer="Sim. Pela relacao que foi aprendida, essa equivalencia continua valida.",
            )
        return ReasoningResult(handled=False)

    def _looks_like_origin_question(self, text: str) -> bool:
        normalized = text.lower()
        triggers = (
            "de onde vem",
            "vem de",
            "como formar",
            "como se forma",
            "o que compoe",
            "o que compõe",
        )
        return any(trigger in normalized for trigger in triggers)

    def _extract_symbol_query(self, text: str) -> str | None:
        patterns = (
            r"\b([A-Za-z0-9_]+)\s*=\s*\?",
            r"\bo que e ([A-Za-z0-9_]+)\b",
            r"\bo que é ([A-Za-z0-9_]+)\b",
            r"\bde onde vem ([A-Za-z0-9_]+)\b",
            r"\bcomo formar ([A-Za-z0-9_]+)\b",
            r"\bo que compoe ([A-Za-z0-9_]+)\b",
            r"\bo que compõe ([A-Za-z0-9_]+)\b",
        )
        lowered = text.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return match.group(1)
        return None

    def _extract_symbols(self, text: str) -> list[str]:
        symbols = re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", text)
        return [symbol for symbol in symbols if symbol.lower() not in {"jarvis", "ultron", "status", "ajuda"}]

    def _related_expressions(self, data: dict[str, Any], symbol: str) -> list[str]:
        canonical = self._canonical_expression(symbol)
        graph = data.get("graph", {})
        queue = [canonical]
        visited = {canonical}
        related: list[str] = []

        while queue:
            current = queue.pop(0)
            for neighbor in graph.get(current, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)
                related.append(self._preferred_display(data, neighbor))

        related = [item for item in related if self._canonical_expression(item) != canonical]
        related.sort(key=lambda item: (0 if any(op in item for op in "+*") else 1, len(item)))
        return related

    def _are_equivalent(self, data: dict[str, Any], left: str, right: str) -> bool:
        left_key = self._canonical_expression(left)
        right_key = self._canonical_expression(right)
        if left_key == right_key:
            return True

        graph = data.get("graph", {})
        queue = [left_key]
        visited = {left_key}

        while queue:
            current = queue.pop(0)
            for neighbor in graph.get(current, []):
                if neighbor == right_key:
                    return True
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)
        return False

    def _link(self, data: dict[str, Any], left: str, right: str) -> bool:
        left_key = self._canonical_expression(left)
        right_key = self._canonical_expression(right)
        if not left_key or not right_key or left_key == right_key:
            return False

        graph = data.setdefault("graph", {})
        display = data.setdefault("display", {})
        graph.setdefault(left_key, [])
        graph.setdefault(right_key, [])

        changed = False
        if right_key not in graph[left_key]:
            graph[left_key].append(right_key)
            changed = True
        if left_key not in graph[right_key]:
            graph[right_key].append(left_key)
            changed = True

        display.setdefault(left_key, left.strip())
        display.setdefault(right_key, right.strip())
        return changed

    def _extract_equations(self, text: str) -> list[tuple[str, str]]:
        equations: list[tuple[str, str]] = []
        for left, right in EQUATION_RE.findall(text):
            clean_left = left.strip(" .,;:!?")
            clean_right = right.strip(" .,;:!?")
            if clean_left and clean_right:
                equations.append((clean_left, clean_right))
        return equations

    def _canonical_expression(self, expression: str) -> str:
        compact = expression.replace(" ", "").lower()
        operation = OPERATION_RE.match(compact)
        if not operation:
            return compact

        left, operator, right = operation.groups()
        if operator in {"+", "*"}:
            ordered = sorted([left, right])
            return f"{ordered[0]}{operator}{ordered[1]}"
        return compact

    def _preferred_display(self, data: dict[str, Any], expression: str) -> str:
        key = self._canonical_expression(expression)
        return data.get("display", {}).get(key, expression)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"graph": {}, "display": {}}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"graph": {}, "display": {}}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
