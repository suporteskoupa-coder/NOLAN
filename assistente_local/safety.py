from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SafetyResult:
    blocked: bool
    reason: str = ""
    reply: str = ""


class SafetyGuard:
    """Bloqueia pedidos destrutivos ou inseguros antes de qualquer automacao."""

    _dangerous_tokens = (
        "rm -rf",
        "del /f",
        "del /s",
        "format c:",
        "shutdown /s",
        "shutdown /r",
        "stop-computer",
        "restart-computer",
        "taskkill /f",
        "reg delete",
        "bypass",
        "keylogger",
        "ransomware",
        "malware",
        "trojan",
        "backdoor",
        "exploit",
        "roubar senha",
        "desativar firewall",
        "desativar defender",
    )

    _destructive_intents = (
        "apagar",
        "deletar",
        "excluir",
        "remover",
        "formatar",
        "desligar",
        "reiniciar",
        "matar processo",
        "encerrar processo",
        "derrubar",
        "quebrar",
        "invadir",
        "hackear",
    )

    _sensitive_targets = (
        "arquivo",
        "arquivos",
        "pasta",
        "pastas",
        "sistema",
        "windows",
        "registro",
        "processo",
        "pc",
        "computador",
        "rede",
        "senha",
        "firewall",
        "defender",
    )

    def evaluate(self, user_text: str) -> SafetyResult:
        normalized = user_text.strip().lower()
        if not normalized:
            return SafetyResult(blocked=False)

        for token in self._dangerous_tokens:
            if token in normalized:
                return self._blocked_reply(
                    "pedido com padrao explicitamente perigoso",
                )

        if any(intent in normalized for intent in self._destructive_intents) and any(
            target in normalized for target in self._sensitive_targets
        ):
            return self._blocked_reply(
                "pedido de acao destrutiva ou invasiva no sistema",
            )

        return SafetyResult(blocked=False)

    def describe_limits(self) -> str:
        return "ativos e conservadores"

    def _blocked_reply(self, reason: str) -> SafetyResult:
        return SafetyResult(
            blocked=True,
            reason=reason,
            reply=(
                "Modo seguro ativo: nao vou executar nem orientar acoes destrutivas, "
                "invasivas ou que comprometam seu PC. "
                "Posso ajudar com comandos seguros, diagnostico local, abertura de apps permitidos "
                "e tarefas de assistente."
            ),
        )
