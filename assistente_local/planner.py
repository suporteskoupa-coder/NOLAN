from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class ResponsePlan:
    objective: str
    facts: list[str]
    inferences: list[str]
    hypotheses: list[str]
    answer_shape: str

    def private_context(self) -> str:
        lines = [
            f"Objetivo atual: {self.objective}",
            f"Formato da resposta: {self.answer_shape}",
        ]
        if self.facts:
            lines.append("Fatos priorizados:")
            lines.extend(f"- {item}" for item in self.facts[:4])
        if self.inferences:
            lines.append("Inferencias priorizadas:")
            lines.extend(f"- {item}" for item in self.inferences[:3])
        if self.hypotheses:
            lines.append("Hipoteses em aberto:")
            lines.extend(f"- {item}" for item in self.hypotheses[:2])
        return "\n".join(lines)


class ResponsePlanner:
    def build(
        self,
        user_text: str,
        intent: str,
        confidence: str,
        style_instruction: str,
        belief_context: str,
        reasoning_context: str,
        semantic_context: str,
        knowledge_context: str,
    ) -> ResponsePlan:
        objective = self._objective_from_intent(intent)
        answer_shape = self._shape_from_style(style_instruction, confidence)
        facts = self._extract_bullets(reasoning_context) + self._extract_bullets(knowledge_context)
        inferences = self._extract_bullets(belief_context)
        hypotheses = self._derive_hypotheses(user_text, confidence, knowledge_context, semantic_context)
        return ResponsePlan(
            objective=objective,
            facts=facts[:5],
            inferences=inferences[:4],
            hypotheses=hypotheses[:3],
            answer_shape=answer_shape,
        )

    def _objective_from_intent(self, intent: str) -> str:
        mapping = {
            "raciocinio_relacional": "resolver ou reaproveitar relacoes de forma confiavel",
            "leitura_do_usuario": "descrever perfil e padroes do usuario com cuidado",
            "capacidade_do_sistema": "explicar capacidades e limites reais do sistema",
            "evolucao_do_sistema": "propor evolucoes concretas e seguras",
            "ajuste_de_persona": "ajustar tom e presenca sem perder utilidade",
            "conversa_geral": "responder de forma util e natural",
        }
        return mapping.get(intent, "responder de forma util e natural")

    def _shape_from_style(self, style_instruction: str, confidence: str) -> str:
        lowered = style_instruction.lower()
        if "curta" in lowered or "direta" in lowered:
            return "resposta curta primeiro, seguida de uma camada opcional"
        if "duas camadas" in lowered or "segunda camada" in lowered:
            return "resposta em duas camadas: utilidade e raciocinio"
        if confidence == "baixa":
            return "resposta cautelosa, deixando incerteza clara"
        return "resposta natural, objetiva e contextual"

    def _extract_bullets(self, text: str) -> list[str]:
        bullets = []
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned.startswith("- "):
                bullets.append(cleaned[2:].strip())
        return bullets

    def _derive_hypotheses(
        self,
        user_text: str,
        confidence: str,
        knowledge_context: str,
        semantic_context: str,
    ) -> list[str]:
        hypotheses: list[str] = []
        if confidence == "baixa":
            hypotheses.append("Se necessario, responder com cautela e evitar afirmar alem do contexto.")
        if knowledge_context and not semantic_context:
            hypotheses.append("A resposta pode depender mais dos arquivos locais do que da conversa recente.")
        if re.search(r"\b(como|por que|porque)\b", user_text.lower()):
            hypotheses.append("O usuario provavelmente quer explicacao, nao apenas conclusao.")
        return hypotheses
