from __future__ import annotations

import re
import unicodedata


LETTER_CLASS = r"A-Za-z\u00C0-\u017F"
ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
WORD_END_RE = re.compile(rf"([{LETTER_CLASS}]+)$")
WORD_START_RE = re.compile(rf"^([{LETTER_CLASS}]+)")
PARTIAL_DUPLICATE_RE = re.compile(rf"\b([{LETTER_CLASS}]{{3,8}})\s+([{LETTER_CLASS}]{{5,}})\b")
REPEATED_PARTIAL_DUPLICATE_RE = re.compile(
    rf"\b([{LETTER_CLASS}]{{3,8}})(?:\s+\1)+\s+([{LETTER_CLASS}]{{5,}})\b"
)
REPEATED_WORD_RE = re.compile(rf"\b([{LETTER_CLASS}]{{2,}})([.!?])\s+\1\b", re.IGNORECASE)
REPEATED_PLAIN_WORD_RE = re.compile(rf"\b([{LETTER_CLASS}]{{2,}})\s+\1\b", re.IGNORECASE)

COMMON_REPLACEMENTS = {
    "\ufffd": "",
    "\u0103": "\u00e3",
    "\u0102": "\u00c3",
    "\u0119": "\u00ea",
    "\u0118": "\u00ca",
    "voc\u0119": "voc\u00ea",
    "Voc\u0119": "Voc\u00ea",
    "coer\u0119ncia": "coer\u00eancia",
    "s\u0103o": "s\u00e3o",
    "n\u0103o": "n\u00e3o",
    "vocÃª": "você",
    "VocÃª": "Você",
    "nÃ£o": "não",
    "presenÃ§a": "presença",
    "relaÃ§Ã£o": "relação",
    "relaÃ§Ãµes": "relações",
    "lÃ³gica": "lógica",
    "raciocÃ­nio": "raciocínio",
    "invisÃ­vel": "invisível",
}


def sanitize_assistant_text(text: str) -> str:
    cleaned = ANSI_RE.sub("", text)
    cleaned = cleaned.replace("\r", "")
    cleaned = "".join(
        char
        for char in cleaned
        if char in ("\n", "\t") or unicodedata.category(char)[0] != "C"
    )
    cleaned = _repair_wrapped_lines(cleaned)
    for source, target in COMMON_REPLACEMENTS.items():
        cleaned = cleaned.replace(source, target)
    cleaned = _remove_partial_duplicates(cleaned)
    cleaned = REPEATED_WORD_RE.sub(r"\1\2", cleaned)
    cleaned = REPEATED_PLAIN_WORD_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" ?\n ?", "\n", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.strip()


def _repair_wrapped_lines(text: str) -> str:
    blocks = [block for block in text.split("\n\n") if block.strip()]
    if not blocks:
        return text.strip()

    repaired_blocks: list[str] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        merged = lines[0]
        for line in lines[1:]:
            merged = _merge_line(merged, line)
        repaired_blocks.append(merged)

    return "\n\n".join(repaired_blocks)


def _merge_line(current: str, next_line: str) -> str:
    prev_match = WORD_END_RE.search(current)
    next_match = WORD_START_RE.search(next_line)

    if prev_match and next_match:
        previous_word = prev_match.group(1)
        next_word = next_match.group(1)
        if (
            previous_word.lower() != next_word.lower()
            and len(previous_word) <= 5
            and next_word.lower().startswith(previous_word.lower())
        ):
            current = current[: -len(previous_word)] + next_word
            remainder = next_line[len(next_word) :].lstrip()
            return f"{current} {remainder}".rstrip()

    if current.endswith("-"):
        return current[:-1] + next_line

    return f"{current} {next_line}".strip()


def _remove_partial_duplicates(text: str) -> str:
    def replace_repeated(match: re.Match[str]) -> str:
        fragment = match.group(1)
        full_word = match.group(2)
        if full_word.lower().startswith(fragment.lower()) and len(full_word) >= len(fragment) + 3:
            return full_word
        return match.group(0)

    def replace(match: re.Match[str]) -> str:
        first = match.group(1)
        second = match.group(2)
        if second.lower().startswith(first.lower()) and len(second) >= len(first) + 3:
            return second
        return match.group(0)

    previous = None
    while previous != text:
        previous = text
        text = REPEATED_PARTIAL_DUPLICATE_RE.sub(replace_repeated, text)
        text = PARTIAL_DUPLICATE_RE.sub(replace, text)
    return text
