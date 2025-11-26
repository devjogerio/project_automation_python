from src.gui.theme import toggle_theme


def format_message(who: str, text: str) -> str:
    """Formata mensagem para histórico de chat.

    Comentário de função: retorna string padronizada usada
    pelos componentes de chat, permitindo teste lógico.
    """
    return f"[{who}] {text}\n"


def test_toggle_theme_three_steps() -> None:
    """Verifica alternância encadeada Light->Dark->Light."""
    assert toggle_theme("Light") == "Dark"
    assert toggle_theme("Dark") == "Light"


def test_format_message() -> None:
    assert format_message("Você", "Olá") == "[Você] Olá\n"

