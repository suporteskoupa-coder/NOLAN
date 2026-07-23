from __future__ import annotations

from .config import Settings
from .engine import AssistantEngine
from .ui import AssistantWindow


def run() -> None:
    settings = Settings()
    app = AssistantWindow(AssistantEngine(settings))
    app.mainloop()
