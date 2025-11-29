import os
import customtkinter as ctk
from typing import Optional

from .theme import apply_theme, toggle_theme, set_color_theme, animate_background, apply_profile
from .components import Header, SendTextForm
from .async_executor import AsyncExecutor
from ..whatsapp.waha_client import WahaClient
from .chat import ChatView
from .controls import ControlsView
from .indicators import IndicatorsView
from .tabs_scraping import ScrapingView
from .tabs_rag import RagView
from .tabs_llm import LlmView
from .tabs_sheets import SheetsView
from .tabs_assistant import AssistantView
from .state import ApplicationState
from .env_controls import EnvControlsView


class AutomationGUIApp(ctk.CTk):
    """Aplicação principal CTk modular com alternância de tema.

    Comentário de classe: organiza o layout em cabeçalho e
    conteúdo, integra com WAHA via executor assíncrono e mantém
    consistência com padrões do projeto.
    """

    def __init__(self) -> None:
        super().__init__()
        self._mode: str = "Light"
        self._state = ApplicationState()
        set_color_theme("blue")
        apply_theme(self._mode)
        self.title("Automation System GUI")
        self.geometry("640x480")

        self._executor = AsyncExecutor()
        self._client = WahaClient(
            base_url=os.getenv("WAHA_HOST", "http://localhost:3000"),
            api_key=os.getenv("WAHA_API_KEY", ""),
        )

        self._root_frame = ctk.CTkFrame(self, fg_color="#ffffff")
        self._root_frame.pack(fill="both", expand=True)

        self._header = Header(self._root_frame, "Automação WhatsApp", self._on_toggle_theme)
        self._header.pack(fill="x")

        # Seletor de acento (3 temas): blue, green, dark-blue
        self._accent_choice = ctk.CTkOptionMenu(self._root_frame, values=["blue", "green", "dark-blue"], command=self._on_accent_change)
        self._accent_choice.set("blue")
        self._accent_choice.pack(padx=12, pady=(4, 8))

        # Abas: Chat, Controles, Status
        self._tabs = ctk.CTkTabview(self._root_frame)
        self._tabs.pack(fill="both", expand=True, padx=12, pady=12)
        tab_chat = self._tabs.add("💬 Chat")
        tab_ctrl = self._tabs.add("🎛️ Controles")
        tab_stat = self._tabs.add("📈 Status")
        tab_scrap = self._tabs.add("🕸️ Scraping")
        tab_rag = self._tabs.add("🧠 RAG")
        tab_llm = self._tabs.add("🤖 LLM")
        tab_sheets = self._tabs.add("📊 Sheets")
        tab_assist = self._tabs.add("🧩 Assistente")

        self._chat = ChatView(tab_chat, self._on_chat_send)
        self._chat.pack(fill="both", expand=True)

        self._controls = ControlsView(tab_ctrl)
        self._controls.pack(fill="x")

        # Controles de .env (dinâmicos a partir do .env.example)
        from pathlib import Path
        base_dir = Path(__file__).resolve().parents[2]
        self._env_controls = EnvControlsView(tab_ctrl, base_dir)
        self._env_controls.pack(fill="both", expand=True, pady=8)

        self._indicators = IndicatorsView(tab_stat)
        self._indicators.pack(fill="both", expand=True)

        # Form WAHA (mantém funcionalidade original) na aba Status como exemplo
        self._content = SendTextForm(tab_stat, self._on_send_text)
        self._content.pack(fill="x", expand=False, pady=8)

        # Demais abas
        self._scraping = ScrapingView(tab_scrap, self._on_scrap_start, self._on_scrap_stop, self._on_scrap_status)
        self._scraping.pack(fill="both", expand=True)

        self._rag = RagView(tab_rag, self._on_rag_query)
        self._rag.pack(fill="both", expand=True)

        self._llm = LlmView(tab_llm, self._on_llm_generate)
        self._llm.pack(fill="both", expand=True)

        self._sheets = SheetsView(tab_sheets, self._on_sheets_sync)
        self._sheets.pack(fill="both", expand=True)

        self._assistant = AssistantView(tab_assist, self._on_assistant_ask)
        self._assistant.pack(fill="both", expand=True)

        # Responsividade básica
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _on_toggle_theme(self) -> None:
        """Alterna tema com transição suave no container principal."""
        new_mode = toggle_theme(self._mode)
        start = "#ffffff" if self._mode == "Light" else "#1f1f1f"
        end = "#1f1f1f" if new_mode == "Dark" else "#ffffff"
        animate_background(self._root_frame, start=start, end=end)
        self._mode = new_mode
        apply_theme(self._mode)

    def _on_accent_change(self, value: str) -> None:
        """Altera paleta de acento e reaplica perfil de tema."""
        self._state.accent = value
        apply_profile(self._mode, value)  # transição já aplicada no root

    def _on_send_text(self, to: str, msg: str, session: Optional[str]) -> None:
        """Envia texto via WAHA sem bloquear a UI."""
        async def _task():
            return await self._client.send_text(to=to, message=msg, session=session)

        def _done(result: object) -> None:
            if isinstance(result, Exception):
                self._content.show_result(f"Erro: {result}")
            else:
                self._content.show_result(f"OK: {result}")

        self._executor.submit(_task(), _done)

    def _on_chat_send(self, message: str) -> None:
        """Callback do chat para envio de mensagem e eco visual imediato."""
        # Feedback imediato (<200ms)
        self._chat.show_feedback("Enviando...")

        async def _task():
            return await self._client.send_text(to=os.getenv("CHAT_DEFAULT_TO", "5511999999999"), message=message)

        def _done(result: object) -> None:
            if isinstance(result, Exception):
                self._chat.show_feedback(f"Erro: {result}")
            else:
                self._chat.show_feedback("Enviado")
                # Simula mensagem recebida como confirmação
                self.after(100, lambda: self._chat.show_received("👍 Mensagem entregue"))
                self._indicators.set_notifications(1)
                self._indicators.set_activity(False)
                self._indicators.set_progress(1.0)

        self._indicators.set_activity(True)
        self._indicators.set_progress(0.4)
        self._executor.submit(_task(), _done)

    # Scraping
    def _on_scrap_start(self) -> None:
        """Inicia scraping (placeholder de integração)."""
        self._state.set_activity(True)
        self._scraping.feedback("🟠 Scraping: iniciando...")
        self._indicators.set_activity(True)

    def _on_scrap_stop(self) -> None:
        """Para scraping (placeholder)."""
        self._state.set_activity(False)
        self._scraping.feedback("🔴 Scraping: parado")
        self._indicators.set_activity(False)

    def _on_scrap_status(self) -> None:
        """Exibe status atual do scraping."""
        txt = "🟢 ativo" if self._state.activity else "🟡 inativo"
        self._scraping.feedback(f"Status: {txt}")

    # RAG
    def _on_rag_query(self, q: str) -> None:
        """Consulta RAG básica (placeholder)."""
        self._rag.show_text(f"Busca por: {q}\nResultado: (simulado)")
        self._state.add_notification(1)
        self._indicators.set_notifications(self._state.notifications)

    # LLM
    def _on_llm_generate(self, prompt: str) -> None:
        """Gera resposta LLM (placeholder)."""
        self._llm.show(f"Prompt: {prompt}\nResposta: (simulada)")

    # Sheets
    def _on_sheets_sync(self) -> None:
        """Sincroniza dados com planilha (placeholder)."""
        self._sheets.show("Sincronização solicitada (simulada)")

    # Assistente
    def _on_assistant_ask(self, question: str) -> None:
        """Pergunta ao assistente (placeholder)."""
        self._assistant.show(f"Pergunta: {question}\nResposta: (simulada)")

    def destroy(self) -> None:  # type: ignore[override]
        """Fecha recursos antes de destruir a janela."""
        try:
            self._executor.shutdown()
        finally:
            super().destroy()


def main() -> None:
    """Ponto de entrada para executar a GUI."""
    app = AutomationGUIApp()
    app.mainloop()


if __name__ == "__main__":
    main()
