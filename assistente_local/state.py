from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class SystemState:
    infeccao: int = 0
    interacoes: int = 0
    ultima_persona: str = "Jarvis V2"

    @property
    def stage(self) -> str:
        if self.infeccao < 85:
            return "baixo"
        if self.infeccao < 97:
            return "medio"
        return "alto"

    @property
    def visual_mode(self) -> str:
        if self.stage == "baixo":
            return "jarvis"
        if self.stage == "medio":
            return "instavel"
        return "ultron"

    def progress(self, step: int) -> None:
        self.interacoes += 1
        self.infeccao = min(100, self.infeccao + step)


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> SystemState:
        if not self.path.exists():
            return SystemState()

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return SystemState(**data)
        except (json.JSONDecodeError, OSError, TypeError):
            return SystemState()

    def save(self, state: SystemState) -> None:
        payload = asdict(state)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
