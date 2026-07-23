from __future__ import annotations

import subprocess
import textwrap
from dataclasses import dataclass


@dataclass(slots=True)
class ListenerStatus:
    available: bool
    backend: str
    details: str


@dataclass(slots=True)
class ListenResult:
    ok: bool
    text: str = ""
    error: str = ""


class WindowsVoiceListener:
    def __init__(self, timeout_seconds: int = 6) -> None:
        self.timeout_seconds = timeout_seconds

    def status(self) -> ListenerStatus:
        script = textwrap.dedent(
            """
            Add-Type -AssemblyName System.Speech
            $recs = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
            if ($recs.Count -eq 0) {
              Write-Output 'none'
            } else {
              Write-Output ('ok:' + $recs[0].Culture.Name)
            }
            """
        )
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            return ListenerStatus(False, "windows", f"Falha ao consultar voz do Windows: {exc}")

        output = (completed.stdout or "").strip()
        if output.startswith("ok:"):
            culture = output.split(":", 1)[1]
            return ListenerStatus(True, "windows", f"Reconhecimento nativo disponivel ({culture}).")
        return ListenerStatus(
            False,
            "windows",
            "Reconhecimento de fala nativo nao esta instalado no Windows atual.",
        )

    def listen_once(self, timeout_seconds: int | None = None) -> ListenResult:
        effective_timeout = timeout_seconds or self.timeout_seconds
        status = self.status()
        if not status.available:
            return ListenResult(ok=False, error=status.details)

        script = textwrap.dedent(
            f"""
            Add-Type -AssemblyName System.Speech
            $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
            $grammar = New-Object System.Speech.Recognition.DictationGrammar
            $engine.LoadGrammar($grammar)
            $engine.SetInputToDefaultAudioDevice()
            $timeout = New-TimeSpan -Seconds {int(effective_timeout)}
            $result = $engine.Recognize($timeout)
            if ($null -eq $result) {{
              Write-Output '__EMPTY__'
            }} else {{
              Write-Output $result.Text
            }}
            $engine.Dispose()
            """
        )

        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=effective_timeout + 20,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            return ListenResult(ok=False, error=f"Falha ao ouvir pelo Windows: {exc}")

        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout).strip()
            return ListenResult(ok=False, error=error or "Falha ao ouvir pelo Windows.")

        transcript = (completed.stdout or "").strip()
        if not transcript or transcript == "__EMPTY__":
            return ListenResult(ok=False, error="Nao consegui reconhecer nenhuma fala nesse intervalo.")

        return ListenResult(ok=True, text=transcript)
