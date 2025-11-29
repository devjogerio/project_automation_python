import customtkinter as ctk
from typing import Callable


class LlmView(ctk.CTkFrame):
    """Aba LLM com prompt e resposta.

    Comentário de classe: permite digitar prompt e executar
    geração no provedor preferido, exibindo resposta.
    """

    def __init__(self, master: ctk.CTk, on_generate: Callable[[str], None]) -> None:
        super().__init__(master)
        self._prompt = ctk.CTkTextbox(self, height=140)
        self._go = ctk.CTkButton(self, text="Gerar", command=self._handle)
        self._out = ctk.CTkTextbox(self, height=200)

        self._prompt.pack(fill="both", expand=True, padx=12, pady=(12, 8))
        self._go.pack(padx=12, pady=(0, 8))
        self._out.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._on_generate = on_generate

    def _handle(self) -> None:
        text = self._prompt.get("1.0", "end").strip()
        if not text:
            self.show("Digite um prompt.")
            return
        self._on_generate(text)

    def show(self, text: str) -> None:
        self._out.delete("1.0", "end")
        self._out.insert("end", text)

