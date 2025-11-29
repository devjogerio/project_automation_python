import customtkinter as ctk
from typing import Callable


class SheetsView(ctk.CTkFrame):
    """Aba Google Sheets com sincronização.

    Comentário de classe: botão para sincronizar dados e
    área de log/resultado da operação.
    """

    def __init__(self, master: ctk.CTk, on_sync: Callable[[], None]) -> None:
        super().__init__(master)
        self._sync = ctk.CTkButton(self, text="Sincronizar", command=on_sync)
        self._log = ctk.CTkTextbox(self, height=220)
        self._sync.pack(padx=12, pady=(12, 8))
        self._log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def show(self, text: str) -> None:
        self._log.delete("1.0", "end")
        self._log.insert("end", text)

