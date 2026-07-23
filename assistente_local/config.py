from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


def _default_data_dir() -> Path:
    return Path(tempfile.gettempdir()) / "jarvis_ultron_assistant"


def _default_ollama_command() -> str:
    for preferred in Path("C:/Users").glob("*/AppData/Local/Programs/Ollama/ollama.exe"):
        if preferred.exists():
            return str(preferred)
    return os.getenv("OLLAMA_COMMAND", "ollama")


@dataclass(slots=True)
class Settings:
    jarvis_model: str = os.getenv("JARVIS_MODEL", "llama3")
    ultron_model: str = os.getenv("ULTRON_MODEL", "llama3")
    data_dir: Path = _default_data_dir()
    window_width: int = 940
    window_height: int = 760
    memory_limit: int = 12
    infection_step: int = int(os.getenv("INFECTION_STEP", "3"))
    automation_enabled: bool = os.getenv("AUTOMATION_ENABLED", "1") == "1"
    speech_enabled: bool = os.getenv("SPEECH_ENABLED", "1") == "1"
    speech_voice: str = os.getenv("SPEECH_VOICE", "Microsoft Maria Desktop")
    speech_profile: str = os.getenv("SPEECH_PROFILE", "auto")
    subtle_presence_enabled: bool = os.getenv("SUBTLE_PRESENCE_ENABLED", "1") == "1"
    listen_timeout_seconds: int = int(os.getenv("LISTEN_TIMEOUT_SECONDS", "6"))
    ollama_command: str = _default_ollama_command()

    @property
    def memory_file(self) -> Path:
        return self.data_dir / "memoria.json"

    @property
    def state_file(self) -> Path:
        return self.data_dir / "estado.json"

    @property
    def reasoning_file(self) -> Path:
        return self.data_dir / "raciocinio.json"

    @property
    def profile_file(self) -> Path:
        return self.data_dir / "perfil_usuario.json"

    @property
    def beliefs_file(self) -> Path:
        return self.data_dir / "crencas.json"

    @property
    def knowledge_file(self) -> Path:
        return self.data_dir / "base_local.json"
