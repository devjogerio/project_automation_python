import customtkinter as ctk
from typing import Callable


class AssistantView(ctk.CTkFrame):
    """Aba Assistente Virtual com entrada e resposta.

    Comentário de classe: integra com roteador LLM e RAG
    via callback, exibindo resposta ao usuário.
    """

    def __init__(self, master: ctk.CTk, on_ask: Callable[[str], None]) -> None:
        super().__init__(master)
        self._q = ctk.CTkEntry(self, placeholder_text="Pergunte ao assistente...")
        self._ask = ctk.CTkButton(self, text="Perguntar", command=self._handle)
        self._a = ctk.CTkTextbox(self, height=220)

        self._q.pack(fill="x", padx=12, pady=(12, 8))
        self._ask.pack(padx=12, pady=(0, 8))
        self._a.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._on_ask = on_ask

    def _handle(self) -> None:
        t = self._q.get().strip()
        if not t:
            self.show("Digite uma pergunta.")
            return
        self._on_ask(t)

    def show(self, text: str) -> None:
        self._a.delete("1.0", "end")
        self._a.insert("end", text)

