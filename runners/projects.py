#!/usr/bin/env python3
"""Runner de proyectos: informe de estado de Projects/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import orchestrator  # noqa: E402


def main():
    ok, resultado = orchestrator.ejecutar_agente("projects")
    print(resultado)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
