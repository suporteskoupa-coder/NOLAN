from __future__ import annotations

import threading
from dataclasses import dataclass
from tkinter import filedialog

import customtkinter as ctk

from .engine import AssistantEngine, EngineReply
from .listener import ListenResult, WindowsVoiceListener
from .speech import Speaker


THEMES = {
    "jarvis": {"bg": "#07111A", "panel": "#0D1B2A", "panel_alt": "#0A1623", "accent": "#4DA8FF", "text": "#E8F3FF", "badge": "#14324E"},
    "ressonancia": {"bg": "#120F09", "panel": "#1B1710", "panel_alt": "#17120B", "accent": "#E1A23B", "text": "#FFF2DC", "badge": "#3B2A12"},
    "instavel": {"bg": "#081816", "panel": "#0F2421", "panel_alt": "#0B1F1C", "accent": "#69D8B6", "text": "#E8FFF8", "badge": "#133630"},
}


@dataclass(slots=True)
class ChatLine:
    speaker: str
    content: str


class AssistantWindow(ctk.CTk):
    def __init__(self, engine: AssistantEngine) -> None:
        super().__init__()
        self.engine = engine
        self.speaker = Speaker(
            enabled=engine.settings.speech_enabled,
            voice_name=engine.settings.speech_voice,
            profile_name=engine.settings.speech_profile,
        )
        self.listener = WindowsVoiceListener(timeout_seconds=engine.settings.listen_timeout_seconds)
        self.listener_status = self.listener.status()
        self.title("Jarvis V2")
        self.minsize(900, 720)
        self.resizable(True, True)
        self.attributes("-topmost", True)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._current_theme = THEMES["jarvis"]
        self._build_window_geometry()
        self._build_widgets()
        self._apply_theme("jarvis")
        self._refresh_dashboard()

    def _build_window_geometry(self) -> None:
        width = self.engine.settings.window_width
        height = self.engine.settings.window_height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_pos = max(10, screen_width - width - 30)
        y_pos = max(10, screen_height - height - 80)
        self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    def _build_widgets(self) -> None:
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self.header = ctk.CTkFrame(self, corner_radius=22)
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(14, 10))
        self.header.grid_columnconfigure(0, weight=1)
        self.header.grid_columnconfigure(1, weight=0)

        self.title_row = ctk.CTkFrame(self.header, fg_color="transparent")
        self.title_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(16, 6))
        self.title_row.grid_columnconfigure(1, weight=1)

        self.signal_dot = ctk.CTkFrame(self.title_row, width=14, height=14, corner_radius=7)
        self.signal_dot.grid(row=0, column=0, padx=(0, 10), pady=4)

        self.title_label = ctk.CTkLabel(
            self.title_row,
            text="JARVIS V2",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.grid(row=0, column=1, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            self.header,
            text="Nucleo local com memoria, inferencia e presenca controlada",
            font=ctk.CTkFont(size=13),
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        self.status_label = ctk.CTkLabel(
            self.header,
            text="Canal principal online",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 10))

        self.controls = ctk.CTkFrame(self.header, fg_color="transparent")
        self.controls.grid(row=0, column=1, rowspan=3, sticky="e", padx=18, pady=16)

        self.voice_var = ctk.BooleanVar(value=self.engine.settings.speech_enabled)
        self.voice_switch = ctk.CTkSwitch(
            self.controls,
            text="Voz",
            variable=self.voice_var,
            command=self._toggle_voice,
            width=72,
        )
        self.voice_switch.grid(row=0, column=0, sticky="e", pady=(0, 8))

        self.listen_button = ctk.CTkButton(
            self.controls,
            text="Ouvir",
            width=110,
            command=self._start_listening,
        )
        self.listen_button.grid(row=1, column=0, sticky="e", pady=(0, 8))

        self.voice_menu = ctk.CTkOptionMenu(
            self.controls,
            values=self.speaker.available_voices,
            command=self._change_voice,
            width=210,
        )
        self.voice_menu.set(self.speaker.voice_name)
        self.voice_menu.grid(row=2, column=0, sticky="e")

        self.badge_row = ctk.CTkFrame(self.header, fg_color="transparent")
        self.badge_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))
        self.badge_row.grid_columnconfigure(0, weight=1)
        self.badge_row.grid_columnconfigure(1, weight=1)
        self.badge_row.grid_columnconfigure(2, weight=1)
        self.badge_row.grid_columnconfigure(3, weight=1)

        self.safe_badge = self._make_badge(self.badge_row, "Seguro: ativo")
        self.safe_badge.grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.memory_badge = self._make_badge(self.badge_row, "Memoria: recente")
        self.memory_badge.grid(row=0, column=1, sticky="w", padx=6)

        self.presence_badge = self._make_badge(self.badge_row, "Presenca: calma")
        self.presence_badge.grid(row=0, column=2, sticky="w", padx=6)

        self.listen_badge = self._make_badge(self.badge_row, self._listener_badge_text())
        self.listen_badge.grid(row=0, column=3, sticky="w", padx=(6, 0))

        self.chat_panel = ctk.CTkFrame(self, corner_radius=22)
        self.chat_panel.grid(row=1, column=0, sticky="nsew", padx=(14, 8), pady=8)
        self.chat_panel.grid_columnconfigure(0, weight=1)
        self.chat_panel.grid_rowconfigure(1, weight=1)

        self.chat_header = ctk.CTkLabel(
            self.chat_panel,
            text="Canal de Conversa",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.chat_header.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.chat_box = ctk.CTkTextbox(
            self.chat_panel,
            corner_radius=18,
            wrap="word",
            font=ctk.CTkFont(size=14),
        )
        self.chat_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.chat_box.insert(
            "end",
            "Sistema iniciado.\n"
            "Jarvis V2 aguardando sua chamada.\n"
            "Use o painel lateral para memoria, arquivos e base local.\n",
        )
        self.chat_box.configure(state="disabled")

        self.side_panel = ctk.CTkFrame(self, corner_radius=22)
        self.side_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 14), pady=8)
        self.side_panel.grid_columnconfigure(0, weight=1)
        self.side_panel.grid_rowconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(self.side_panel, corner_radius=18)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self.tabs.add("Painel")
        self.tabs.add("Memoria")
        self.tabs.add("Arquivos")

        self._build_panel_tab()
        self._build_memory_tab()
        self._build_files_tab()

        self.input_frame = ctk.CTkFrame(self, corner_radius=22)
        self.input_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(8, 14))
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Digite sua mensagem...",
            height=46,
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=16)
        self.entry.bind("<Return>", self._on_submit)

        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="Enviar",
            width=110,
            command=self._send_message,
        )
        self.send_button.grid(row=0, column=1, padx=(0, 16), pady=16)

    def _build_panel_tab(self) -> None:
        panel = self.tabs.tab("Painel")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        self.panel_summary = ctk.CTkLabel(
            panel,
            text="Painel cognitivo",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        )
        self.panel_summary.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        self.refresh_panel_button = ctk.CTkButton(
            panel,
            text="Atualizar painel",
            command=self._refresh_dashboard,
        )
        self.refresh_panel_button.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        self.panel_box = ctk.CTkTextbox(panel, corner_radius=14, wrap="word")
        self.panel_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_memory_tab(self) -> None:
        panel = self.tabs.tab("Memoria")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        self.memory_box = ctk.CTkTextbox(panel, corner_radius=14, wrap="word")
        self.memory_box.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 10))

        self.memory_note_entry = ctk.CTkEntry(
            panel,
            placeholder_text="Fixar nota na memoria principal...",
            height=40,
        )
        self.memory_note_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.memory_note_entry.bind("<Return>", self._remember_note)

        self.memory_buttons = ctk.CTkFrame(panel, fg_color="transparent")
        self.memory_buttons.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.memory_buttons.grid_columnconfigure(0, weight=1)
        self.memory_buttons.grid_columnconfigure(1, weight=1)

        self.remember_button = ctk.CTkButton(
            self.memory_buttons,
            text="Fixar nota",
            command=self._remember_note,
        )
        self.remember_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.refresh_memory_button = ctk.CTkButton(
            self.memory_buttons,
            text="Atualizar memoria",
            command=self._refresh_dashboard,
        )
        self.refresh_memory_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_files_tab(self) -> None:
        panel = self.tabs.tab("Arquivos")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        self.import_button = ctk.CTkButton(
            panel,
            text="Importar arquivos",
            command=self._import_files,
        )
        self.import_button.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        self.file_search_entry = ctk.CTkEntry(
            panel,
            placeholder_text="Buscar na base local...",
            height=40,
        )
        self.file_search_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.file_search_entry.bind("<Return>", self._search_files)

        self.file_buttons = ctk.CTkFrame(panel, fg_color="transparent")
        self.file_buttons.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.file_buttons.grid_columnconfigure(0, weight=1)
        self.file_buttons.grid_columnconfigure(1, weight=1)

        self.search_button = ctk.CTkButton(
            self.file_buttons,
            text="Buscar",
            command=self._search_files,
        )
        self.search_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.clear_files_button = ctk.CTkButton(
            self.file_buttons,
            text="Limpar base",
            command=self._clear_local_knowledge,
        )
        self.clear_files_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.files_box = ctk.CTkTextbox(panel, corner_radius=14, wrap="word")
        self.files_box.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _make_badge(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent,
            text=text,
            corner_radius=12,
            padx=10,
            pady=5,
            font=ctk.CTkFont(size=11, weight="bold"),
        )

    def _listener_badge_text(self) -> str:
        return "Ouvir: pronto" if self.listener_status.available else "Ouvir: indisponivel"

    def _append_chat(self, line: ChatLine) -> None:
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"\n{line.speaker}: {line.content}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def _set_box_text(self, box: ctk.CTkTextbox, content: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", content)
        box.configure(state="disabled")

    def _on_submit(self, _event: object) -> str:
        self._send_message()
        return "break"

    def _send_message(self) -> None:
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.entry.delete(0, "end")
        self._append_chat(ChatLine("Voce", user_text))
        self.send_button.configure(state="disabled", text="...")

        worker = threading.Thread(target=self._run_assistant, args=(user_text,), daemon=True)
        worker.start()

    def _run_assistant(self, user_text: str) -> None:
        reply = self.engine.handle_message(user_text)
        self.after(0, lambda: self._apply_reply(reply))

    def _apply_reply(self, reply: EngineReply) -> None:
        self._append_chat(ChatLine(reply.speaker, reply.content))
        self._apply_theme(reply.visual_mode)
        self.status_label.configure(text=self._status_text(reply))
        self.safe_badge.configure(text=f"Seguro: {reply.metadata.get('safe_mode', 'ativo')}")
        self.memory_badge.configure(text=f"Memoria: {reply.metadata.get('memory_state', 'recente')}")
        self.presence_badge.configure(text=self._presence_label(reply))
        self.listen_badge.configure(text=self._listener_badge_text())
        self.send_button.configure(state="normal", text="Enviar")
        self.speaker.speak(reply.content, style=reply.metadata.get("speech_style", "normal"))
        self._refresh_dashboard()

    def _toggle_voice(self) -> None:
        self.speaker.set_enabled(self.voice_var.get())

    def _change_voice(self, voice_name: str) -> None:
        self.speaker.set_voice(voice_name)

    def _refresh_dashboard(self) -> None:
        snapshot = self.engine.dashboard_snapshot()
        self._set_box_text(
            self.panel_box,
            snapshot["status"] + "\n\nPerfil:\n" + snapshot["profile"] + "\n\nBase local:\n" + snapshot["knowledge_summary"],
        )
        self._set_box_text(
            self.memory_box,
            "Perfil:\n"
            + snapshot["profile"]
            + "\n\nCrencas:\n"
            + snapshot["beliefs"]
            + "\n\nMemoria relevante:\n"
            + snapshot["memory"],
        )
        self._set_box_text(self.files_box, "Fontes indexadas:\n" + snapshot["knowledge"])
        self.listener_status = self.listener.status()
        self.listen_badge.configure(text=self._listener_badge_text())
        if self.listener_status.available:
            self.listen_button.configure(state="normal")
        else:
            self.listen_button.configure(state="disabled")

    def _remember_note(self, _event: object | None = None) -> str | None:
        note = self.memory_note_entry.get().strip()
        if not note:
            return None
        message = self.engine.remember_note(note)
        self.memory_note_entry.delete(0, "end")
        self._append_chat(ChatLine("Sistema", message))
        self._refresh_dashboard()
        return "break"

    def _import_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Importar arquivos para a base local",
            filetypes=[
                ("Arquivos suportados", "*.txt *.md *.py *.json *.toml *.yaml *.yml *.csv *.log *.ini *.cfg *.html *.css *.js *.ts *.tsx *.ps1 *.bat"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not paths:
            return
        message = self.engine.index_local_files(list(paths))
        self._append_chat(ChatLine("Sistema", message))
        self._refresh_dashboard()

    def _search_files(self, _event: object | None = None) -> str | None:
        query = self.file_search_entry.get().strip()
        if not query:
            self._refresh_dashboard()
            return None
        result = self.engine.search_local_knowledge(query)
        self._set_box_text(self.files_box, result)
        return "break"

    def _clear_local_knowledge(self) -> None:
        message = self.engine.clear_local_knowledge()
        self._append_chat(ChatLine("Sistema", message))
        self._refresh_dashboard()

    def _start_listening(self) -> None:
        self.listener_status = self.listener.status()
        if not self.listener_status.available:
            self.status_label.configure(text=self.listener_status.details)
            self.listen_badge.configure(text=self._listener_badge_text())
            return

        self.listen_button.configure(state="disabled", text="Ouvindo...")
        worker = threading.Thread(target=self._listen_once, daemon=True)
        worker.start()

    def _listen_once(self) -> None:
        result = self.listener.listen_once()
        self.after(0, lambda: self._apply_listen_result(result))

    def _apply_listen_result(self, result: ListenResult) -> None:
        self.listen_button.configure(state="normal", text="Ouvir")
        if not result.ok:
            self.status_label.configure(text=result.error)
            return

        self.entry.delete(0, "end")
        self.entry.insert(0, result.text)
        self.status_label.configure(text="Fala reconhecida. Enviando...")
        self._send_message()

    def _status_text(self, reply: EngineReply) -> str:
        mode = reply.metadata.get("mode", "core")
        confidence = reply.metadata.get("confidence", "alta")
        presence = reply.metadata.get("presence", "quiet")

        if mode == "shadow":
            return "Camada observadora em foco"
        if presence == "rare":
            return "Ressonancia baixa, mas perceptivel"
        if reply.visual_mode == "ressonancia":
            return "Nucleo em ressonancia leve"
        return f"Nucleo sincronizado | confianca {confidence}"

    def _presence_label(self, reply: EngineReply) -> str:
        mapping = {
            "quiet": "Presenca: calma",
            "resonant": "Presenca: sutil",
            "rare": "Presenca: precisa",
            "observer": "Presenca: observadora",
        }
        return mapping.get(reply.metadata.get("presence", "quiet"), "Presenca: calma")

    def _apply_theme(self, theme_key: str) -> None:
        theme = THEMES[theme_key]
        self._current_theme = theme

        self.configure(fg_color=theme["bg"])
        self.header.configure(fg_color=theme["panel"])
        self.input_frame.configure(fg_color=theme["panel"])
        self.chat_panel.configure(fg_color=theme["panel"])
        self.side_panel.configure(fg_color=theme["panel"])
        self.chat_box.configure(
            fg_color=theme["panel_alt"],
            text_color=theme["text"],
            border_color=theme["accent"],
            border_width=1,
        )
        for box in (self.panel_box, self.memory_box, self.files_box):
            box.configure(
                fg_color=theme["panel_alt"],
                text_color=theme["text"],
                border_color=theme["accent"],
                border_width=1,
            )
        self.entry.configure(
            fg_color=theme["bg"],
            text_color=theme["text"],
            border_color=theme["accent"],
        )
        self.file_search_entry.configure(
            fg_color=theme["bg"],
            text_color=theme["text"],
            border_color=theme["accent"],
        )
        self.memory_note_entry.configure(
            fg_color=theme["bg"],
            text_color=theme["text"],
            border_color=theme["accent"],
        )
        for button in (
            self.send_button,
            self.listen_button,
            self.import_button,
            self.search_button,
            self.clear_files_button,
            self.refresh_panel_button,
            self.remember_button,
            self.refresh_memory_button,
        ):
            button.configure(fg_color=theme["accent"], hover_color=theme["accent"])
        self.signal_dot.configure(fg_color=theme["accent"])
        self.title_label.configure(text_color=theme["text"])
        self.subtitle_label.configure(text_color=theme["text"])
        self.chat_header.configure(text_color=theme["text"])
        self.panel_summary.configure(text_color=theme["text"])
        self.status_label.configure(text_color=theme["accent"])
        self.voice_switch.configure(text_color=theme["text"], progress_color=theme["accent"])
        self.voice_menu.configure(
            fg_color=theme["bg"],
            button_color=theme["accent"],
            button_hover_color=theme["accent"],
            text_color=theme["text"],
        )
        for badge in (self.safe_badge, self.memory_badge, self.presence_badge, self.listen_badge):
            badge.configure(fg_color=theme["badge"], text_color=theme["text"])
