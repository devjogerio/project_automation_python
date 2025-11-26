import customtkinter as ctk


class IndicatorsView(ctk.CTkFrame):
    """Aba de indicadores com progresso e ícones de status.

    Comentário de classe: exibe barra de progresso e
    ícones/labels de conexão, atividade e notificações.
    """

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self._progress = ctk.CTkProgressBar(self)
        self._progress.set(0.0)
        self._status_conn = ctk.CTkLabel(self, text="🟡 Conexão: desconhecida")
        self._status_activity = ctk.CTkLabel(self, text="🟡 Atividade: ociosa")
        self._status_notify = ctk.CTkLabel(self, text="🔔 Notificações: nenhuma")

        self._progress.pack(fill="x", padx=12, pady=(12, 6))
        self._status_conn.pack(fill="x", padx=12, pady=(0, 4))
        self._status_activity.pack(fill="x", padx=12, pady=(0, 4))
        self._status_notify.pack(fill="x", padx=12, pady=(0, 8))

    def set_progress(self, value: float) -> None:
        """Atualiza a barra de progresso (0.0–1.0)."""
        self._progress.set(max(0.0, min(1.0, value)))

    def set_connected(self, ok: bool) -> None:
        """Define estado de conexão (ícone e texto)."""
        icon = "🟢" if ok else "🔴"
        text = "Conectado" if ok else "Desconectado"
        self._status_conn.configure(text=f"{icon} Conexão: {text}")

    def set_activity(self, active: bool) -> None:
        """Define indicador de atividade."""
        icon = "🟠" if active else "🟡"
        text = "processando" if active else "ociosa"
        self._status_activity.configure(text=f"{icon} Atividade: {text}")

    def set_notifications(self, count: int) -> None:
        """Atualiza contador de notificações."""
        self._status_notify.configure(text=f"🔔 Notificações: {count}")

