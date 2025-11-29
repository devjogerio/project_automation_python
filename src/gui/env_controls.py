from pathlib import Path
from typing import Dict, List, Tuple
import os
import customtkinter as ctk


SENSITIVE_HINTS = ("KEY", "SECRET", "PASSWORD", "TOKEN")


def parse_env_example(example_path: Path) -> List[Tuple[str, str]]:
    """Lê o .env.example e retorna lista de pares (nome, valor_default)."""
    pairs: List[Tuple[str, str]] = []
    if not example_path.exists():
        return pairs
    for line in example_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            name, val = line.split("=", 1)
            pairs.append((name.strip(), val.strip()))
    return pairs


def read_env_values(env_path: Path) -> Dict[str, str]:
    """Lê um arquivo .env e retorna dict de valores (se existir)."""
    data: Dict[str, str] = {}
    if not env_path.exists():
        return data
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def write_env_values(env_path: Path, values: Dict[str, str]) -> None:
    """Escreve valores em formato .env no caminho especificado."""
    lines = [f"{k}={v}" for k, v in values.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class EnvControlsView(ctk.CTkFrame):
    """Aba de controles de ambiente baseada em .env.example e .env."""

    def __init__(self, master: ctk.CTk, base_dir: Path) -> None:
        super().__init__(master)
        self._base_dir = base_dir
        self._example = base_dir / ".env.example"
        self._env = base_dir / ".env"
        self._values: Dict[str, str] = {}

        self._title = ctk.CTkLabel(self, text="⚙️ Configurações do Ambiente (.env)", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.pack(fill="x", padx=12, pady=(12, 8))

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self._actions = ctk.CTkFrame(self)
        self._actions.pack(fill="x", padx=12, pady=(0, 12))
        self._btn_load = ctk.CTkButton(self._actions, text="Carregar .env", command=self._load_env)
        self._btn_save_local = ctk.CTkButton(self._actions, text="Salvar .env.local", command=self._save_env_local)
        self._btn_export_env = ctk.CTkButton(self._actions, text="Exportar .env (confirmar)", command=self._export_env_confirm)
        self._btn_load.pack(side="left", padx=6)
        self._btn_save_local.pack(side="left", padx=6)
        self._btn_export_env.pack(side="left", padx=6)

        self._status = ctk.CTkLabel(self, text="", wraplength=520)
        self._status.pack(fill="x", padx=12, pady=(0, 8))

        self._inputs: Dict[str, ctk.CTkEntry] = {}
        self._secure_flags: Dict[str, bool] = {}
        self._build_inputs()

    def _build_inputs(self) -> None:
        """Cria entradas de acordo com .env.example."""
        pairs = parse_env_example(self._example)
        env_vals = read_env_values(self._env)
        for name, default in pairs:
            row = ctk.CTkFrame(self._scroll)
            row.pack(fill="x", padx=8, pady=6)
            label = ctk.CTkLabel(row, text=name, width=220)
            label.pack(side="left")

            is_sensitive = any(h in name.upper() for h in SENSITIVE_HINTS)
            self._secure_flags[name] = is_sensitive
            entry = ctk.CTkEntry(row, show="*" if is_sensitive else None)
            entry.pack(side="left", fill="x", expand=True, padx=8)

            val = env_vals.get(name, os.getenv(name, default))
            entry.insert(0, val or "")
            self._inputs[name] = entry

            if is_sensitive:
                toggle = ctk.CTkSwitch(row, text="Mostrar", command=lambda e=entry: e.configure(show=None if e.cget("show") else "*"))
                toggle.pack(side="left", padx=8)

    def _collect_values(self) -> Dict[str, str]:
        """Coleta valores atuais dos campos."""
        out: Dict[str, str] = {}
        for k, entry in self._inputs.items():
            out[k] = entry.get().strip()
        return out

    def _load_env(self) -> None:
        """Carrega valores do .env se existir e preenche os campos."""
        data = read_env_values(self._env)
        if not data:
            self._status.configure(text="Nenhum .env encontrado; usando defaults.")
            return
        for k, v in data.items():
            if k in self._inputs:
                self._inputs[k].delete(0, "end")
                self._inputs[k].insert(0, v)
        self._status.configure(text=".env carregado.")

    def _save_env_local(self) -> None:
        """Salva os valores em .env.local no diretório do projeto."""
        vals = self._collect_values()
        target = self._base_dir / ".env.local"
        write_env_values(target, vals)
        self._status.configure(text=f"Valores salvos em {target.name}.")

    def _export_env_confirm(self) -> None:
        """Abre modal de confirmação para exportar valores em .env."""
        top = ctk.CTkToplevel(self)
        top.title("Confirmar Exportação")
        ctk.CTkLabel(top, text="Confirmar escrita em .env? (não versionar segredos)").pack(padx=16, pady=(16, 8))
        btns = ctk.CTkFrame(top)
        btns.pack(fill="x", padx=16, pady=(0, 16))

        def _ok() -> None:
            vals = self._collect_values()
            write_env_values(self._env, vals)
            self._status.configure(text=".env atualizado com sucesso.")
            top.destroy()

        def _cancel() -> None:
            self._status.configure(text="Exportação cancelada.")
            top.destroy()

        ctk.CTkButton(btns, text="Confirmar", command=_ok).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Cancelar", command=_cancel).pack(side="left", padx=8)

