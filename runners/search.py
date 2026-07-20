#!/usr/bin/env python3
"""Runner de búsqueda: python3 ~/Jarvis/runners/search.py "consulta"."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents import document_finder  # noqa: E402


def main():
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("Uso: python3 search.py <consulta>")
        sys.exit(1)
    print(document_finder.run(query=query))


if __name__ == "__main__":
    main()
