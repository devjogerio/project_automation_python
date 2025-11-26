import os
import pytest

from src.gui.theme import toggle_theme


@pytest.mark.parametrize("start,expected", [("Light", "Dark"), ("Dark", "Light")])
def test_toggle_theme(start: str, expected: str) -> None:
    assert toggle_theme(start) == expected


def test_no_env_side_effects() -> None:
    """Garante que alternância de tema não depende de variáveis de ambiente."""
    env_before = dict(os.environ)
    _ = toggle_theme("Light")
    assert dict(os.environ) == env_before
