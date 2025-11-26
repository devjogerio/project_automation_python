import customtkinter as ctk
from typing import Callable


class Header(ctk.CTkFrame):
    """Cabeçalho com título e alternância de tema.

    Comentário de classe: componente reutilizável para o topo,
    com botão de alternância claro/escuro e espaço para ações.
    """

    def __init__(self, master: ctk.CTk, title: str, on_toggle_theme: Callable[[], None]) -> None:
        super().__init__(master)
        self._title = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold"))
        self._title.pack(side="left", padx=12, pady=10)

        self._toggle = ctk.CTkSwitch(self, text="Tema", command=on_toggle_theme)
        self._toggle.pack(side="right", padx=12)


class SendTextForm(ctk.CTkFrame):
    """Formulário simples para enviar mensagem via WAHA.

    Comentário de classe: encapsula campos e botão de envio,
    chamando callback com dados validados.
    """

    def __init__(self, master: ctk.CTk, on_submit: Callable[[str, str, str | None], None]) -> None:
        super().__init__(master)
        self._to = ctk.CTkEntry(self, placeholder_text="Número destino (E164)")
        self._msg = ctk.CTkTextbox(self, height=100)
        self._session = ctk.CTkEntry(self, placeholder_text="Sessão (opcional)")
        self._submit = ctk.CTkButton(self, text="Enviar", command=self._handle_submit)
        self._status = ctk.CTkLabel(self, text="", wraplength=360)

        self._to.pack(fill="x", padx=12, pady=(8, 4))
        self._session.pack(fill="x", padx=12, pady=(4, 4))
        self._msg.pack(fill="both", padx=12, pady=(4, 8), expand=True)
        self._submit.pack(padx=12, pady=(0, 8))
        self._status.pack(fill="x", padx=12, pady=(0, 8))

        self._on_submit = on_submit

    def _handle_submit(self) -> None:
        """Captura os valores e invoca o callback do app."""
        to = self._to.get().strip()
        msg = self._msg.get("1.0", "end").strip()
        session = self._session.get().strip() or None
        if not to or not msg:
            self._status.configure(text="Preencha 'destino' e 'mensagem'.")
            return
        self._status.configure(text="Enviando...")
        self._on_submit(to, msg, session)

    def show_result(self, text: str) -> None:
        """Atualiza etiqueta de status com o resultado."""
        self._status.configure(text=text)

