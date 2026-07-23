from __future__ import annotations

import subprocess
import webbrowser
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AutomationResult:
    handled: bool
    message: str = ""


class SafeAutomation:
    """Executa apenas acoes explicitamente permitidas."""

    def try_handle(self, user_text: str) -> AutomationResult:
        normalized = user_text.strip().lower()

        if not normalized:
            return AutomationResult(handled=False)

        if "que horas" in normalized or "hora atual" in normalized:
            now = datetime.now().strftime("%H:%M")
            return AutomationResult(handled=True, message=f"Sao {now}.")

        if "abrir calculadora" in normalized:
            return self._run(["calc.exe"], "Abrindo calculadora.")

        if "abrir bloco de notas" in normalized or "abrir notepad" in normalized:
            return self._run(["notepad.exe"], "Abrindo bloco de notas.")

        if "abrir explorador" in normalized or "abrir arquivos" in normalized:
            return self._run(["explorer.exe"], "Abrindo explorador de arquivos.")

        if "abrir navegador" in normalized:
            try:
                webbrowser.open("https://www.google.com", new=2)
                return AutomationResult(handled=True, message="Abrindo navegador.")
            except webbrowser.Error:
                return AutomationResult(
                    handled=True,
                    message="Nao consegui abrir o navegador padrao.",
                )

        return AutomationResult(handled=False)

    def _run(self, command: list[str], ok_message: str) -> AutomationResult:
        try:
            subprocess.Popen(command)
            return AutomationResult(handled=True, message=ok_message)
        except OSError as exc:
            return AutomationResult(
                handled=True,
                message=f"Falha na automacao permitida: {exc}",
            )

