import customtkinter as ctk


class ControlsView(ctk.CTkFrame):
    """Aba de controles com feedback em tempo real.

    Comentário de classe: inclui slider, toggle e rótulos de
    feedback imediato para demonstrar responsividade (<200ms).
    """

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self._slider = ctk.CTkSlider(self, from_=0, to=100, command=self._on_slider)
        self._toggle = ctk.CTkSwitch(self, text="Ativar", command=self._on_toggle)
        self._value = ctk.CTkLabel(self, text="Valor: 0")
        self._state = ctk.CTkLabel(self, text="Estado: OFF")

        self._slider.pack(fill="x", padx=12, pady=(12, 6))
        self._toggle.pack(padx=12, pady=(0, 6))
        self._value.pack(fill="x", padx=12, pady=(0, 4))
        self._state.pack(fill="x", padx=12, pady=(0, 8))

    def _on_slider(self, val: float) -> None:
        """Atualiza rótulo de valor em tempo real ao mover slider."""
        self._value.configure(text=f"Valor: {int(val)}")

    def _on_toggle(self) -> None:
        """Atualiza estado ON/OFF imediatamente."""
        state = "ON" if self._toggle.get() else "OFF"
        self._state.configure(text=f"Estado: {state}")

