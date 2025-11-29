import customtkinter as ctk
from typing import Callable


class RagView(ctk.CTkFrame):
    """Aba RAG com consulta de conhecimento.

    Comentário de classe: campo de entrada para query e
    botão de executar, apresentando resultado simplificado.
    """

    def __init__(self, master: ctk.CTk, on_query: Callable[[str], None]) -> None:
        super().__init__(master)
        self._entry = ctk.CTkEntry(self, placeholder_text="Consulta RAG...")
        self._run = ctk.CTkButton(self, text="Buscar", command=self._handle)
        self._result = ctk.CTkTextbox(self, height=180)

        self._entry.pack(fill="x", padx=12, pady=(12, 8))
        self._run.pack(padx=12, pady=(0, 8))
        self._result.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._on_query = on_query

    def _handle(self) -> None:
        q = self._entry.get().strip()
        if not q:
            self.show_text("Digite uma consulta.")
            return
        self._on_query(q)

    def show_text(self, text: str) -> None:
        self._result.delete("1.0", "end")
        self._result.insert("end", text)

