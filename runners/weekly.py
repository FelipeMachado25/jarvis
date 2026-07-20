#!/usr/bin/env python3
"""Runner semanal: genera el briefing completo (lo lanza launchd el domingo)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents import weekly  # noqa: E402


def main():
    try:
        print(weekly.run(guardar=True))
    except Exception as e:
        print("Error generando el briefing: %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
