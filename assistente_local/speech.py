from __future__ import annotations

import io
import inspect
import queue
import re
import subprocess
import threading
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MARKDOWN_RE = re.compile(r"[*_`#>-]+")
WHITESPACE_RE = re.compile(r"\s+")

PIPER_VOICE_LABEL = "Piper pt-BR Neural"
WINDOWS_VOICES = (
    "Microsoft Maria Desktop",
    "Microsoft Zira Desktop",
)

SPEECH_STYLES = {
    "normal": {"pause_ms": 120, "windows_rate": 0},
    "focused": {"pause_ms": 170, "windows_rate": -1},
    "observer": {"pause_ms": 240, "windows_rate": -2},
    "night": {"pause_ms": 280, "windows_rate": -2},
}

SPEECH_REPLACEMENTS = (
    ("A + B", "A mais B"),
    (" + ", " mais "),
    (" = ", " igual a "),
    (" * ", " vezes "),
    (" / ", " dividido por "),
    (" % ", " por cento "),
    ("->", " leva para "),
    (":)", "."),
)


class Speaker:
    """Sintese de voz local com preferencia por Piper e fallback para Windows."""

    def __init__(
        self,
        enabled: bool = True,
        voice_name: str = "Microsoft Maria Desktop",
        profile_name: str = "auto",
    ) -> None:
        self.enabled = enabled
        self.profile_name = profile_name
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._piper_voice: PiperVoice | None = None
        self._available_voices: list[str] = []
        self._load_piper_voice()
        self._build_available_voices()
        self.voice_name = self._initial_voice_name(voice_name)
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    @property
    def available_voices(self) -> list[str]:
        return list(self._available_voices)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def set_voice(self, voice_name: str) -> None:
        self.voice_name = self._resolve_voice_name(voice_name)

    def set_profile(self, profile_name: str) -> None:
        self.profile_name = profile_name

    def speak(self, text: str, style: str = "normal") -> None:
        if not self.enabled:
            return

        cleaned = self._prepare_for_speech(text)
        if not cleaned:
            return

        self._clear_pending_items()
        self._queue.put((cleaned, style))

    def _build_available_voices(self) -> None:
        if self._piper_voice is not None:
            self._available_voices.append(PIPER_VOICE_LABEL)
        self._available_voices.extend(WINDOWS_VOICES)

    def _resolve_voice_name(self, voice_name: str) -> str:
        if voice_name in self._available_voices:
            return voice_name
        if PIPER_VOICE_LABEL in self._available_voices:
            return PIPER_VOICE_LABEL
        return self._available_voices[0]

    def _initial_voice_name(self, voice_name: str) -> str:
        if voice_name == WINDOWS_VOICES[0] and PIPER_VOICE_LABEL in self._available_voices:
            return PIPER_VOICE_LABEL
        return self._resolve_voice_name(voice_name)

    def _load_piper_voice(self) -> None:
        model_path = Path(__file__).resolve().parent.parent / "models" / "piper" / "pt_BR-faber-medium.onnx"
        config_path = model_path.with_suffix(model_path.suffix + ".json")
        if not model_path.exists() or not config_path.exists():
            return

        espeak_data_dir = self._find_espeak_data_dir()
        if espeak_data_dir is None:
            return

        try:
            self._piper_voice = PiperVoice.load(
                model_path=model_path,
                config_path=config_path,
                espeak_data_dir=espeak_data_dir,
            )
        except Exception:
            self._piper_voice = None

    def _find_espeak_data_dir(self) -> Path | None:
        try:
            base_dir = Path(inspect.getfile(PiperVoice)).resolve().parent
        except (OSError, TypeError):
            return None

        preferred = base_dir / "espeak-ng-data"
        if preferred.exists():
            return preferred

        package_root = base_dir.parent
        fallback = package_root / "piper" / "espeak-ng-data"
        if fallback.exists():
            return fallback

        return None

    def _clear_pending_items(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

    def _run(self) -> None:
        while True:
            text, style = self._queue.get()
            try:
                if self.enabled:
                    self._speak_blocking(text, style)
            finally:
                self._queue.task_done()

    def _prepare_for_speech(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""

        cleaned = MARKDOWN_RE.sub("", cleaned)
        cleaned = cleaned.replace("\r", " ")
        cleaned = cleaned.replace("\n", ". ")
        cleaned = cleaned.replace("|", ". ")
        for source, target in SPEECH_REPLACEMENTS:
            cleaned = cleaned.replace(source, target)
        cleaned = cleaned.replace("...", ".")
        cleaned = cleaned.replace("..", ".")
        cleaned = WHITESPACE_RE.sub(" ", cleaned)
        return cleaned.strip(" .") + "."

    def _effective_style(self, style: str) -> str:
        if self.profile_name != "auto" and self.profile_name in SPEECH_STYLES:
            return self.profile_name
        if style in SPEECH_STYLES:
            return style
        return "normal"

    def _split_chunks(self, text: str) -> list[str]:
        chunks = [chunk.strip() for chunk in SENTENCE_SPLIT_RE.split(text) if chunk.strip()]
        return chunks or [text.strip()]

    def _speak_blocking(self, text: str, style: str) -> None:
        effective_style = self._effective_style(style)
        if self.voice_name == PIPER_VOICE_LABEL and self._piper_voice is not None:
            if self._speak_with_piper(text, effective_style):
                return

        self._speak_with_windows(text, effective_style)

    def _synthesize_piper_audio(self, text: str) -> tuple[np.ndarray, int] | None:
        if self._piper_voice is None:
            return None

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            self._piper_voice.synthesize_wav(text, wav_file)

        wav_buffer.seek(0)
        with wave.open(wav_buffer, "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            frames = wav_file.readframes(wav_file.getnframes())

        audio = np.frombuffer(frames, dtype=np.int16)
        if channels > 1:
            audio = audio.reshape(-1, channels)
        return audio.astype(np.float32) / 32768.0, sample_rate

    def _speak_with_piper(self, text: str, style: str) -> bool:
        config = SPEECH_STYLES.get(style, SPEECH_STYLES["normal"])
        try:
            chunks = self._split_chunks(text)
            for index, chunk in enumerate(chunks):
                audio = self._synthesize_piper_audio(chunk)
                if audio is None:
                    return False
                samples, sample_rate = audio
                sd.play(samples, sample_rate, blocking=True)
                if index < len(chunks) - 1:
                    time.sleep(config["pause_ms"] / 1000.0)
            return True
        except Exception:
            return False

    def _windows_voice_name(self) -> str:
        if self.voice_name in WINDOWS_VOICES:
            return self.voice_name
        return WINDOWS_VOICES[0]

    def _speak_with_windows(self, text: str, style: str) -> None:
        chunks = self._split_chunks(text)
        if not chunks:
            return

        config = SPEECH_STYLES.get(style, SPEECH_STYLES["normal"])
        selected_voice = self._windows_voice_name().replace("'", "''")
        pause_ms = int(config["pause_ms"])
        rate = int(config["windows_rate"])
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"try {{ $speaker.SelectVoice('{selected_voice}') }} catch {{ }}; "
            f"$speaker.Rate = {rate}; "
            "$speaker.Volume = 100; "
            "$content = [Console]::In.ReadToEnd(); "
            "$parts = $content -split '(?<=[.!?])\\s+'; "
            "foreach ($part in $parts) { "
            "  if (-not [string]::IsNullOrWhiteSpace($part)) { "
            "    $speaker.Speak($part.Trim()); "
            f"    Start-Sleep -Milliseconds {pause_ms}; "
            "  } "
            "}"
        )

        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script],
                input=" ".join(chunks),
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=90,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return
