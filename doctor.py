#!/usr/bin/env python3
"""Jarvis doctor: verifica y repara todo lo necesario (idempotente).

Ejecutar: python3 ~/Jarvis/doctor.py
Se puede correr las veces que haga falta; crea el vault, la config y
comprueba que Ollama + el modelo estén listos.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import config as jconfig  # noqa: E402
from core.model_client import OllamaClient  # noqa: E402

HOME = Path.home()
VAULT = jconfig.ruta_vault()
CARPETAS = jconfig.carpetas()
CONFIG_DIR = HOME / ".jarvis"


def paso(nombre, ok, detalle=""):
    print("  %s %s %s" % ("✓" if ok else "✗", nombre, detalle))
    return ok


def main():
    print("🔧 Jarvis doctor\n")
    todo_ok = True

    # 1. Estructura del vault
    for carpeta in CARPETAS:
        (VAULT / carpeta).mkdir(parents=True, exist_ok=True)
    todo_ok &= paso("Vault Obsidian", VAULT.exists(), str(VAULT))

    # 2. Config y logs
    (CONFIG_DIR / "logs").mkdir(parents=True, exist_ok=True)
    config = CONFIG_DIR / "config.json"
    if not config.exists():
        config.write_text(
            json.dumps(
                {
                    "vault": str(jconfig.VAULT_DEFAULT).replace(str(HOME), "~"),
                    "user_name": jconfig.USER_DEFAULT,
                    "carpetas": list(jconfig.CARPETAS_DEFAULT),
                    "briefing_semanal": {"dia": "domingo", "hora": "20:00"},
                    "log_level": "INFO",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    todo_ok &= paso("Config", config.exists(), str(config))

    # 3. Binarios instalados
    todo_ok &= paso("Ollama instalado", shutil.which("ollama") is not None)
    obsidian = Path("/Applications/Obsidian.app").exists()
    todo_ok &= paso("Obsidian instalado", obsidian)
    paso(
        "OMNI instalado",
        Path("/Applications/Omni.app").exists(),
        "(opcional, búsqueda semántica)",
    )

    # 4. Servidor + modelo
    cliente = OllamaClient()
    try:
        cliente.asegurar_servidor()
        vivo = True
    except Exception:
        vivo = False
    todo_ok &= paso("Servidor Ollama", vivo, cliente.endpoint)
    if vivo and not cliente.modelo_descargado():
        print("  … descargando %s (una sola vez)" % cliente.config["model"])
        subprocess.run(["ollama", "pull", cliente.config["model"]], check=False)
    todo_ok &= paso(
        "Modelo %s" % cliente.config["model"], vivo and cliente.modelo_descargado()
    )

    # 5. Permisos de los scripts
    for script in (HOME / "Jarvis" / "automation").glob("*.sh"):
        script.chmod(0o755)
    paso("Scripts ejecutables", True)

    print(
        "\n%s"
        % ("✅ Jarvis listo." if todo_ok else "⚠️ Hay pasos pendientes (ver arriba).")
    )
    sys.exit(0 if todo_ok else 1)


if __name__ == "__main__":
    main()
