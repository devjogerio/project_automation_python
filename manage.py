#!/usr/bin/env python3
import os
import sys
from pathlib import Path


def main():
    """Ponto de entrada do Django, ajustando o PYTHONPATH para incluir `src/`."""
    root = Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.append(str(src))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.webapp.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
