from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class OllamaResult:
    ok: bool
    text: str
    error: str = ""


@dataclass(slots=True)
class OllamaStatus:
    available: bool
    details: str


class OllamaClient:
    def __init__(self, command: str = "ollama") -> None:
        self.command = command

    def generate(self, model: str, prompt: str, timeout: int = 120) -> OllamaResult:
        try:
            completed = subprocess.run(
                [self.command, "run", model],
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return OllamaResult(
                ok=False,
                text="",
                error="Ollama nao encontrado. Instale e deixe o binario acessivel no PATH.",
            )
        except subprocess.TimeoutExpired:
            return OllamaResult(
                ok=False,
                text="",
                error="Ollama excedeu o tempo limite da resposta.",
            )

        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout).strip()
            return OllamaResult(ok=False, text="", error=error or "Falha ao consultar o Ollama.")

        return OllamaResult(ok=True, text=completed.stdout.strip())

    def status(self, timeout: int = 10) -> OllamaStatus:
        try:
            completed = subprocess.run(
                [self.command, "list"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return OllamaStatus(
                available=False,
                details="Ollama nao encontrado no PATH.",
            )
        except subprocess.TimeoutExpired:
            return OllamaStatus(
                available=False,
                details="Ollama nao respondeu a tempo.",
            )

        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout).strip()
            return OllamaStatus(
                available=False,
                details=details or "Falha ao consultar o Ollama.",
            )

        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if len(lines) <= 1:
            return OllamaStatus(
                available=True,
                details="Ollama encontrado, mas nenhum modelo foi listado.",
            )

        listed_models = []
        for line in lines[1:4]:
            listed_models.append(line.split()[0])
        return OllamaStatus(
            available=True,
            details=f"Ollama online. Modelos detectados: {', '.join(listed_models)}.",
        )
