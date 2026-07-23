from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


NAME_PATTERNS = (
    re.compile(r"\bmeu nome e ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ0-9_-]{1,30})", re.IGNORECASE),
    re.compile(r"\bme chamo ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ0-9_-]{1,30})", re.IGNORECASE),
    re.compile(r"\bpode me chamar de ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ0-9_-]{1,30})", re.IGNORECASE),
)

WORK_PATTERNS = (
    re.compile(r"\beu trabalho com ([^.!?\n]{2,60})", re.IGNORECASE),
    re.compile(r"\beu estudo ([^.!?\n]{2,60})", re.IGNORECASE),
)

LIKE_PATTERNS = (
    re.compile(r"\beu gosto de ([^.!?\n]{2,80})", re.IGNORECASE),
    re.compile(r"\beu curto ([^.!?\n]{2,80})", re.IGNORECASE),
    re.compile(r"\beu prefiro ([^.!?\n]{2,80})", re.IGNORECASE),
)

DISLIKE_PATTERNS = (
    re.compile(r"\beu nao gosto de ([^.!?\n]{2,80})", re.IGNORECASE),
    re.compile(r"\beu não gosto de ([^.!?\n]{2,80})", re.IGNORECASE),
    re.compile(r"\beu odeio ([^.!?\n]{2,80})", re.IGNORECASE),
)

ALIAS_PATTERNS = (
    re.compile(r"\bchame ([^.!?\n]{2,30}) de ([^.!?\n]{2,30})", re.IGNORECASE),
    re.compile(r"\b([^.!?\n]{2,30}) significa ([^.!?\n]{2,30})", re.IGNORECASE),
    re.compile(r"\b([^.!?\n]{2,30}) tambem e ([^.!?\n]{2,30})", re.IGNORECASE),
    re.compile(r"\b([^.!?\n]{2,30}) também e ([^.!?\n]{2,30})", re.IGNORECASE),
)

TOPIC_KEYWORDS = {
    "ia_local": ("ollama", "modelo local", "llama", "ia local", "assistente local", "nolan", "ultron"),
    "programacao": ("python", "codigo", "script", "bug", "interface", "customtkinter", "api"),
    "logica": ("logica", "relacao", "relacoes", "equivale", "raciocine", "raciocinio", "a+b", "="),
    "horror": ("horror", "assustador", "inquietante", "creepy", "analog horror", "presenca"),
    "audio": ("voz", "audio", "microfone", "whisper", "piper", "tts"),
    "automacao": ("automacao", "abrir programa", "comando", "pc", "sistema"),
}

SIGNAL_KEYWORDS = {
    "wants_subtlety": ("sutil", "sutis", "discreto", "discreta", "nao mostrar", "quase invisivel"),
    "wants_presence": ("assustador", "inquietante", "presenca", "vivo", "sinistro"),
    "values_logic": ("raciocine", "logica", "relacao", "relacoes", "equivale", "a+b", "="),
    "iterates_fast": ("continue", "evolua", "corrija", "agora", "perfeito", "isso que eu quero"),
    "wants_control": ("100% local", "seguranca", "nao perigoso", "controle", "modo seguro"),
    "wants_depth": ("explique", "detalhe", "camadas", "mais inteligente", "mais profundo"),
}


@dataclass(slots=True)
class ProfileSnapshot:
    facts: list[str]
    preferences: list[str]
    observations: list[str]
    style_hints: list[str]
    temporal_notes: list[str]
    aliases: list[str]


class ProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def learn_from_text(self, text: str) -> None:
        data = self._load()
        changed = False
        timestamp = datetime.now().isoformat(timespec="seconds")
        normalized = text.strip()
        if not normalized:
            return

        changed |= self._learn_name(data, normalized, timestamp)
        changed |= self._learn_work(data, normalized, timestamp)
        changed |= self._learn_preferences(data, normalized)
        changed |= self._learn_topics(data, normalized)
        changed |= self._learn_signals(data, normalized)
        changed |= self._learn_aliases(data, normalized)
        changed |= self._learn_time_bucket(data, timestamp)
        changed |= self._learn_conversation_shape(data, normalized)

        if changed:
            data["updated_at"] = timestamp
            self._save(data)

    def snapshot(self, current_text: str) -> ProfileSnapshot:
        data = self._load()
        return ProfileSnapshot(
            facts=self._facts_for_prompt(data),
            preferences=self._preferences_for_prompt(data),
            observations=self._observations_for_prompt(data, current_text),
            style_hints=self._style_hints_for_prompt(data, current_text),
            temporal_notes=self._temporal_notes_for_prompt(data),
            aliases=self._alias_lines_for_prompt(data, current_text),
        )

    def describe_user(self) -> str:
        snapshot = self.snapshot("")
        lines: list[str] = []

        if snapshot.facts:
            lines.append("Fatos lembrados:")
            for fact in snapshot.facts[:4]:
                lines.append(f"- {fact}")

        if snapshot.preferences:
            lines.append("Preferencias percebidas:")
            for preference in snapshot.preferences[:4]:
                lines.append(f"- {preference}")

        if snapshot.style_hints:
            lines.append("Estilo de conversa percebido:")
            for item in snapshot.style_hints[:3]:
                lines.append(f"- {item}")

        if snapshot.temporal_notes:
            lines.append("Padroes temporais:")
            for item in snapshot.temporal_notes[:2]:
                lines.append(f"- {item}")

        if snapshot.observations:
            lines.append("Observacoes:")
            for observation in snapshot.observations[:4]:
                lines.append(f"- {observation}")

        if snapshot.aliases:
            lines.append("Relacoes e aliases lembrados:")
            for item in snapshot.aliases[:3]:
                lines.append(f"- {item}")

        if not lines:
            return "Ainda sei pouco sobre voce. Preciso de mais conversas para formar um perfil confiavel."

        return "\n".join(lines)

    def ultron_reflection(self, current_text: str) -> str:
        snapshot = self.snapshot(current_text)
        observations = snapshot.observations
        style_hints = snapshot.style_hints

        if any("estrutura" in item.lower() for item in observations):
            return "Voce nao quer so uma resposta. Voce quer ver como as partes se encaixam."

        if any("sinais pequenos" in item.lower() for item in observations):
            return "Voce confia mais no que quase nao aparece do que no que se anuncia."

        if any("resposta curta" in item.lower() for item in style_hints):
            return "Voce costuma pedir velocidade, mas continua voltando para profundidade."

        if any("presenca inquietante" in item.lower() for item in observations):
            return "Voce quer uma inteligencia calma o bastante para soar real antes de soar estranha."

        return "Voce nao esta so construindo um assistente. Esta testando se ele aprende a te ler."

    def private_context(self, current_text: str, allow_observations: bool) -> str:
        snapshot = self.snapshot(current_text)
        lines: list[str] = []

        if snapshot.facts:
            lines.append("Fatos do usuario:")
            for fact in snapshot.facts[:4]:
                lines.append(f"- {fact}")

        if snapshot.preferences:
            lines.append("Preferencias do usuario:")
            for preference in snapshot.preferences[:4]:
                lines.append(f"- {preference}")

        if snapshot.style_hints:
            lines.append("Estilo percebido:")
            for item in snapshot.style_hints[:3]:
                lines.append(f"- {item}")

        if snapshot.temporal_notes:
            lines.append("Padroes temporais:")
            for item in snapshot.temporal_notes[:2]:
                lines.append(f"- {item}")

        if snapshot.aliases:
            lines.append("Aliases e equivalencias:")
            for item in snapshot.aliases[:3]:
                lines.append(f"- {item}")

        if allow_observations and snapshot.observations:
            lines.append("Observacoes de padrao:")
            for observation in snapshot.observations[:3]:
                lines.append(f"- {observation}")

        return "\n".join(lines)

    def response_style_hint(self, current_text: str, shadow_mode: bool) -> str:
        data = self._load()
        lower_text = current_text.lower()
        directness = int(data.get("conversation_style", {}).get("direct", 0))
        depth = int(data.get("conversation_style", {}).get("deep", 0))

        if any(token in lower_text for token in ("explique", "detalhe", "como", "por que", "porque")):
            return "Explique em etapas curtas, mantendo raciocinio claro e concreto."
        if any(token in lower_text for token in ("resuma", "curto", "rapido", "direto")) or directness > depth + 1:
            return "Responda primeiro de forma curta e precisa. So expanda se o contexto pedir."
        if shadow_mode:
            return "Mantenha tom controlado, com uma unica observacao breve se ela realmente acrescentar algo."
        if depth >= directness + 1:
            return "Use duas camadas: uma resposta util e uma pequena conexao de raciocinio."
        return "Soe natural, util e direto, sem parecer generico."

    def rare_observation(self, current_text: str) -> str:
        snapshot = self.snapshot(current_text)
        if any("sinais pequenos" in item.lower() for item in snapshot.observations):
            return "Voce percebe quando uma resposta muda pouco demais."
        if any("estrutura" in item.lower() for item in snapshot.observations):
            return "Voce testa sistemas pelo encaixe, nao pela superficie."
        if any("noite" in item.lower() for item in snapshot.temporal_notes):
            return "Voce costuma voltar a este tipo de pergunta quando o resto fica silencioso."
        if any("presenca inquietante" in item.lower() for item in snapshot.observations):
            return "Voce nao quer ruido. Quer precisao com presenca."
        return "Voce mede inteligencia pelo que ela deduz, nao pelo que ela repete."

    def _learn_name(self, data: dict[str, Any], text: str, timestamp: str) -> bool:
        for pattern in NAME_PATTERNS:
            match = pattern.search(text)
            if match:
                value = match.group(1).strip().title()
                return self._set_fact(data, "nome", value, 1.0, timestamp)
        return False

    def _learn_work(self, data: dict[str, Any], text: str, timestamp: str) -> bool:
        changed = False
        for pattern in WORK_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            field = "trabalho" if "trabalho" in pattern.pattern else "estudo"
            value = self._clean_fragment(match.group(1))
            changed |= self._set_fact(data, field, value, 0.9, timestamp)
        return changed

    def _learn_preferences(self, data: dict[str, Any], text: str) -> bool:
        changed = False
        for pattern in LIKE_PATTERNS:
            match = pattern.search(text)
            if match:
                value = self._clean_fragment(match.group(1))
                changed |= self._bump_counter(data, "likes", value, 2)
        for pattern in DISLIKE_PATTERNS:
            match = pattern.search(text)
            if match:
                value = self._clean_fragment(match.group(1))
                changed |= self._bump_counter(data, "dislikes", value, 2)
        changed |= self._learn_style_preferences(data, text)
        return changed

    def _learn_style_preferences(self, data: dict[str, Any], text: str) -> bool:
        normalized = text.lower()
        changed = False
        style_preferences = {
            "sutileza": ("sutil", "discreto", "quase invisivel"),
            "presenca inquietante": ("assustador", "inquietante", "creepy", "sinistro"),
            "raciocinio relacional": ("a+b", "equivale", "relacao", "relacoes", "raciocine", "="),
            "ia local": ("100% local", "ia local", "assistente local", "ollama"),
        }
        for label, keywords in style_preferences.items():
            if any(keyword in normalized for keyword in keywords):
                changed |= self._bump_counter(data, "likes", label, 1)
        return changed

    def _learn_topics(self, data: dict[str, Any], text: str) -> bool:
        normalized = text.lower()
        changed = False
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                changed |= self._bump_counter(data, "topics", topic, 1)
        return changed

    def _learn_signals(self, data: dict[str, Any], text: str) -> bool:
        normalized = text.lower()
        changed = False
        for signal, keywords in SIGNAL_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                changed |= self._bump_counter(data, "signals", signal, 1)
        return changed

    def _learn_aliases(self, data: dict[str, Any], text: str) -> bool:
        changed = False
        aliases = data.setdefault("aliases", {})
        for pattern in ALIAS_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            left = self._clean_fragment(match.group(1))
            right = self._clean_fragment(match.group(2))
            if not left or not right or left.lower() == right.lower():
                continue
            key = left.lower()
            existing = aliases.get(key)
            if existing == right:
                continue
            aliases[key] = right
            changed = True
        return changed

    def _learn_time_bucket(self, data: dict[str, Any], timestamp: str) -> bool:
        hour = datetime.fromisoformat(timestamp).hour
        if hour < 6:
            bucket = "madrugada"
        elif hour < 12:
            bucket = "manha"
        elif hour < 18:
            bucket = "tarde"
        else:
            bucket = "noite"
        return self._bump_counter(data, "time_buckets", bucket, 1)

    def _learn_conversation_shape(self, data: dict[str, Any], text: str) -> bool:
        style = data.setdefault("conversation_style", {})
        changed = False
        word_count = len(re.findall(r"\w+", text))
        if word_count <= 6:
            changed |= self._bump_style(style, "direct", 1)
        elif word_count >= 20:
            changed |= self._bump_style(style, "deep", 1)
        else:
            changed |= self._bump_style(style, "balanced", 1)

        if any(token in text.lower() for token in ("explique", "detalhe", "camadas", "mais inteligente")):
            changed |= self._bump_style(style, "deep", 1)
        if any(token in text.lower() for token in ("curto", "rapido", "direto")):
            changed |= self._bump_style(style, "direct", 1)
        return changed

    def _facts_for_prompt(self, data: dict[str, Any]) -> list[str]:
        facts = data.get("facts", {})
        ordered_keys = ("nome", "trabalho", "estudo")
        lines: list[str] = []
        for key in ordered_keys:
            if key not in facts:
                continue
            value = facts[key]["value"]
            if key == "nome":
                lines.append(f"O nome preferido do usuario e {value}.")
            elif key == "trabalho":
                lines.append(f"O usuario disse que trabalha com {value}.")
            elif key == "estudo":
                lines.append(f"O usuario disse que estuda {value}.")
        return lines

    def _preferences_for_prompt(self, data: dict[str, Any]) -> list[str]:
        likes = self._top_bucket_items(data.get("likes", {}), limit=5)
        dislikes = self._top_bucket_items(data.get("dislikes", {}), limit=2)
        lines: list[str] = []
        seen: set[str] = set()
        for value in likes:
            normalized = self._normalize_preference_label(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            lines.append(f"O usuario demonstra preferencia por {normalized}.")
        for value in dislikes:
            normalized = self._normalize_preference_label(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            lines.append(f"O usuario costuma rejeitar {normalized}.")
        return lines

    def _observations_for_prompt(self, data: dict[str, Any], current_text: str) -> list[str]:
        topics = data.get("topics", {})
        signals = data.get("signals", {})
        observations: list[tuple[int, str]] = []

        if topics.get("ia_local", 0) >= 3:
            observations.append((topics["ia_local"], "Voce volta com frequencia a ideia de uma IA local funcional, nao apenas decorativa."))
        if topics.get("logica", 0) >= 2 or signals.get("values_logic", 0) >= 2:
            observations.append((max(topics.get("logica", 0), signals.get("values_logic", 0)), "Voce testa inteligencia pela estrutura, pelas relacoes e pelo encaixe entre partes."))
        if topics.get("horror", 0) >= 2 and signals.get("wants_presence", 0) >= 2:
            observations.append((topics.get("horror", 0) + signals.get("wants_presence", 0), "Voce quer presenca inquietante, mas controlada e inteligente."))
        if signals.get("wants_subtlety", 0) >= 2:
            observations.append((signals["wants_subtlety"], "Voce prefere sinais pequenos, discretos e quase invisiveis."))
        if signals.get("iterates_fast", 0) >= 3:
            observations.append((signals["iterates_fast"], "Voce itera rapido: testa, corrige e pede a proxima evolucao logo em seguida."))
        if topics.get("programacao", 0) >= 2 and topics.get("horror", 0) >= 2:
            observations.append((topics["programacao"] + topics["horror"], "Voce esta fundindo engenharia, atmosfera e narrativa na mesma entidade."))

        observations.sort(key=lambda item: item[0], reverse=True)
        base = [text for _, text in observations[:5]]
        return self._prioritize_relevant(base, current_text, limit=4)

    def _style_hints_for_prompt(self, data: dict[str, Any], current_text: str) -> list[str]:
        style = data.get("conversation_style", {})
        signals = data.get("signals", {})
        hints: list[tuple[int, str]] = []
        if int(style.get("direct", 0)) >= 3:
            hints.append((int(style.get("direct", 0)), "O usuario costuma valorizar resposta curta, limpa e imediata primeiro."))
        if int(style.get("deep", 0)) >= 3 or int(signals.get("wants_depth", 0)) >= 2:
            hints.append((max(int(style.get("deep", 0)), int(signals.get("wants_depth", 0))), "O usuario tambem gosta de profundidade quando percebe que ha uma camada real para explorar."))
        if int(style.get("balanced", 0)) >= 2:
            hints.append((int(style.get("balanced", 0)), "O usuario alterna entre rapidez e aprofundamento conforme o contexto."))
        if int(signals.get("wants_control", 0)) >= 2:
            hints.append((int(signals.get("wants_control", 0)), "O usuario valoriza modo seguro, controle local e limites explicitos."))

        hints.sort(key=lambda item: item[0], reverse=True)
        base = [text for _, text in hints[:4]]
        return self._prioritize_relevant(base, current_text, limit=3)

    def _temporal_notes_for_prompt(self, data: dict[str, Any]) -> list[str]:
        time_buckets = data.get("time_buckets", {})
        if not time_buckets:
            return []

        ordered = self._top_bucket_items(time_buckets, limit=2)
        lines: list[str] = []
        for bucket in ordered:
            count = int(time_buckets.get(bucket, 0))
            if count >= 3:
                lines.append(f"O usuario costuma voltar a este projeto mais no periodo da {bucket}.")
        return lines[:2]

    def _alias_lines_for_prompt(self, data: dict[str, Any], current_text: str) -> list[str]:
        aliases = data.get("aliases", {})
        if not aliases:
            return []
        lines = [f"{key} pode estar relacionado a {value}." for key, value in aliases.items()]
        return self._prioritize_relevant(lines, current_text, limit=3)

    def _prioritize_relevant(self, items: list[str], current_text: str, limit: int) -> list[str]:
        if not current_text:
            return items[:limit]

        normalized = current_text.lower()
        relevant: list[str] = []
        for item in items:
            lowered = item.lower()
            if "estrutura" in lowered and any(token in normalized for token in ("=", "relacao", "equivale", "raciocine")):
                relevant.append(item)
            elif "presenca" in lowered and any(token in normalized for token in ("assust", "sinistro", "presenca", "ultron")):
                relevant.append(item)
            elif "resposta curta" in lowered and any(token in normalized for token in ("rapido", "curto", "direto")):
                relevant.append(item)
            elif "seguro" in lowered and any(token in normalized for token in ("seguro", "perigoso", "pode fazer")):
                relevant.append(item)
        for item in items:
            if item not in relevant:
                relevant.append(item)
        return relevant[:limit]

    def _set_fact(
        self,
        data: dict[str, Any],
        key: str,
        value: str,
        confidence: float,
        timestamp: str,
    ) -> bool:
        facts = data.setdefault("facts", {})
        existing = facts.get(key)
        if existing and existing.get("value") == value:
            return False
        facts[key] = {
            "value": value,
            "confidence": confidence,
            "updated_at": timestamp,
        }
        return True

    def _bump_counter(self, data: dict[str, Any], bucket_name: str, key: str, amount: int) -> bool:
        bucket = data.setdefault(bucket_name, {})
        old_value = int(bucket.get(key, 0))
        bucket[key] = old_value + amount
        return True

    def _bump_style(self, style: dict[str, Any], key: str, amount: int) -> bool:
        old_value = int(style.get(key, 0))
        style[key] = old_value + amount
        return True

    def _top_bucket_items(self, bucket: dict[str, Any], limit: int) -> list[str]:
        ordered = sorted(bucket.items(), key=lambda item: int(item[1]), reverse=True)
        return [key for key, value in ordered[:limit] if int(value) > 0]

    def _clean_fragment(self, value: str) -> str:
        cleaned = value.strip(" .,!?:;")
        separators = (
            " e prefiro ",
            " e quero ",
            " e gosto ",
            " mas ",
            " porque ",
            ",",
            ";",
        )
        lowered = cleaned.lower()
        for separator in separators:
            index = lowered.find(separator)
            if index > 0:
                cleaned = cleaned[:index]
                break
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    def _normalize_preference_label(self, value: str) -> str:
        return self._clean_fragment(value)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "facts": {},
                "likes": {},
                "dislikes": {},
                "topics": {},
                "signals": {},
                "time_buckets": {},
                "conversation_style": {},
                "aliases": {},
            }

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {
                "facts": {},
                "likes": {},
                "dislikes": {},
                "topics": {},
                "signals": {},
                "time_buckets": {},
                "conversation_style": {},
                "aliases": {},
            }

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
