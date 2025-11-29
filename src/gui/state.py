from dataclasses import dataclass


@dataclass
class ApplicationState:
    """Estado global da aplicação GUI.

    Comentário de classe: armazena informações compartilhadas
    entre abas, como tab atual, notificações e conectividade.
    """

    current_tab: str = "Chat"
    notifications: int = 0
    activity: bool = False
    connected: bool = False
    accent: str = "blue"

    def switch_tab(self, name: str) -> None:
        """Atualiza o nome da aba atual e reseta atividade visual."""
        self.current_tab = name
        self.activity = False

    def add_notification(self, count: int = 1) -> None:
        """Incrementa contador de notificações."""
        self.notifications += max(0, count)

    def set_connected(self, ok: bool) -> None:
        """Atualiza flag de conectividade."""
        self.connected = ok

    def set_activity(self, active: bool) -> None:
        """Atualiza estado de atividade."""
        self.activity = active

