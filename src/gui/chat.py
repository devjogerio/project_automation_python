import customtkinter as ctk
from typing import Callable


class ChatView(ctk.CTkFrame):
    """Aba de chat com histórico rolável e ações.

    Comentário de classe: disponibiliza uma área de histórico,
    entrada de texto e botões (enviar, limpar, anexar) com
    indicadores visuais simples para mensagens.
    """

    def __init__(self, master: ctk.CTk, on_send: Callable[[str], None]) -> None:
        super().__init__(master)
        self._history = ctk.CTkTextbox(self, height=240, width=520)
        self._history.configure(state="disabled")
        self._entry = ctk.CTkEntry(self, placeholder_text="Digite sua mensagem...")
        self._btn_send = ctk.CTkButton(self, text="Enviar", command=self._handle_send)
        self._btn_clear = ctk.CTkButton(self, text="Limpar", command=self._handle_clear)
        self._btn_attach = ctk.CTkButton(self, text="Anexar", command=self._handle_attach)
        self._status = ctk.CTkLabel(self, text="", width=520)

        self._history.pack(fill="both", expand=True, padx=12, pady=(12, 6))
        self._entry.pack(fill="x", padx=12, pady=(0, 8))
        row = ctk.CTkFrame(self)
        row.pack(fill="x", padx=12, pady=(0, 8))
        self._btn_send.pack(in_=row, side="left", padx=4)
        self._btn_clear.pack(in_=row, side="left", padx=4)
        self._btn_attach.pack(in_=row, side="left", padx=4)
        self._status.pack(fill="x", padx=12, pady=(0, 8))

        self._on_send = on_send

    def _append(self, who: str, text: str) -> None:
        """Adiciona mensagem ao histórico com etiqueta de remetente."""
        self._history.configure(state="normal")
        self._history.insert("end", f"[{who}] {text}\n")
        self._history.see("end")
        self._history.configure(state="disabled")

    def _handle_send(self) -> None:
        """Callback do botão enviar: atualiza histórico e chama handler."""
        msg = self._entry.get().strip()
        if not msg:
            self._status.configure(text="Digite uma mensagem.")
            return
        self._append("Você", msg)
        self._status.configure(text="Enviando...")
        self._on_send(msg)

    def _handle_clear(self) -> None:
        """Limpa o histórico de chat."""
        self._history.configure(state="normal")
        self._history.delete("1.0", "end")
        self._history.configure(state="disabled")
        self._status.configure(text="Histórico limpo.")

    def _handle_attach(self) -> None:
        """Simula ação de anexar (placeholder de demonstração)."""
        self._status.configure(text="Funcionalidade de anexar em desenvolvimento.")

    def show_received(self, text: str) -> None:
        """Mostra mensagem recebida no histórico."""
        self._append("Contato", text)
        self._status.configure(text="Mensagem recebida.")

    def show_feedback(self, text: str) -> None:
        """Exibe feedback visual abaixo dos botões."""
        self._status.configure(text=text)

