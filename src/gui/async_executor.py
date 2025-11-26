import asyncio
from threading import Thread
from typing import Any, Awaitable, Callable


class AsyncExecutor:
    """Executor assíncrono dedicado para integrar corrotinas com GUI.

    Comentário de classe: cria um loop asyncio em uma thread
    separada, permitindo executar chamadas IO sem bloquear a UI.
    """

    def __init__(self) -> None:
        """Inicializa a thread e o loop asyncio prontos para uso."""
        self._loop = asyncio.new_event_loop()
        self._thread = Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def submit(self, coro: Awaitable[Any], callback: Callable[[Any], None]) -> None:
        """Submete uma corrotina para execução e chama `callback` com o resultado.

        Comentário de função: usado pelos handlers da GUI para
        comunicação com serviços (ex.: WAHA) sem travar a janela.
        """
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _done(_fut: Any) -> None:
            try:
                result = _fut.result()
            except Exception as e:  # noqa: BLE001
                result = e
            callback(result)

        fut.add_done_callback(_done)

    def shutdown(self) -> None:
        """Finaliza o loop e a thread com segurança."""
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=1)

