import customtkinter as ctk
from typing import Callable


class ScrapingView(ctk.CTkFrame):
    """Aba de Web Scraping com controles básicos.

    Comentário de classe: permite iniciar, parar e verificar
    status do scraping, integrando com callbacks do app.
    """

    def __init__(self, master: ctk.CTk, on_start: Callable[[], None], on_stop: Callable[[], None], on_status: Callable[[], None]) -> None:
        super().__init__(master)
        self._btn_start = ctk.CTkButton(self, text="Iniciar", command=on_start)
        self._btn_stop = ctk.CTkButton(self, text="Parar", command=on_stop)
        self._btn_status = ctk.CTkButton(self, text="Status", command=on_status)
        self._label = ctk.CTkLabel(self, text="🕸️ Scraping: pronto")

        self._btn_start.pack(side="left", padx=8, pady=12)
        self._btn_stop.pack(side="left", padx=8, pady=12)
        self._btn_status.pack(side="left", padx=8, pady=12)
        self._label.pack(fill="x", padx=12, pady=(0, 8))

    def feedback(self, text: str) -> None:
        """Mostra feedback textual da operação."""
        self._label.configure(text=text)

