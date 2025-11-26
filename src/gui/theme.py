from typing import Literal
try:
    import customtkinter as ctk  # type: ignore
except Exception:  # noqa: BLE001
    ctk = None  # type: ignore


ThemeMode = Literal["Light", "Dark"]
AccentPalette = Literal["blue", "green", "dark-blue"]


def apply_theme(mode: ThemeMode) -> None:
    """Aplica o tema global do customtkinter.

    Comentário de função: troca aparência entre claro/escuro
    utilizando a API do customtkinter, mantendo consistência
    visual em toda a aplicação.
    """
    if ctk is None:
        raise RuntimeError("customtkinter não disponível para apply_theme")
    ctk.set_appearance_mode(mode)


def toggle_theme(current: ThemeMode) -> ThemeMode:
    """Alterna o tema entre "Light" e "Dark" e retorna o novo modo.

    Comentário de função: usado pelos callbacks de UI para
    alternância de tema com feedback visual.
    """
    return "Dark" if current == "Light" else "Light"


def set_color_theme(name: str = "blue") -> None:
    """Define paleta de cores base do customtkinter.

    Comentário de função: permite alinhar identidade visual
    ao projeto, mudando acentos, botões e sliders.
    """
    if ctk is None:
        raise RuntimeError("customtkinter não disponível para set_color_theme")
    ctk.set_default_color_theme(name)


def apply_profile(mode: ThemeMode, accent: AccentPalette) -> None:
    """Aplica perfil completo de tema (modo + paleta).

    Comentário de função: combina aparência e acentuação de cores
    para fornecer pelo menos três temas modernos.
    """
    set_color_theme(accent)
    apply_theme(mode)


def animate_background(widget: "ctk.CTk", start: str, end: str, steps: int = 10, delay_ms: int = 15) -> None:
    """Realiza transição suave de cor de fundo entre duas cores hex.

    Comentário de função: cria efeito de suavização ao alternar
    temas; usa after para não bloquear o loop principal.
    """
    def _hex_to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    sr, sg, sb = _hex_to_rgb(start)
    er, eg, eb = _hex_to_rgb(end)

    def _step(i: int) -> None:
        t = i / steps
        r = int(sr + (er - sr) * t)
        g = int(sg + (eg - sg) * t)
        b = int(sb + (eb - sb) * t)
        widget.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")
        if i < steps:
            widget.after(delay_ms, lambda: _step(i + 1))

    _step(0)
