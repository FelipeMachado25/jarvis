"""Configuración de usuario de Jarvis (fuente única de verdad).

Lee ``~/.jarvis/config.json`` una sola vez y expone la ruta del vault y
el nombre del usuario. Todo lo personalizable vive aquí para que Jarvis
sea reutilizable: un fork solo edita su ``config.json``, nunca el código.

Cero dependencias externas (solo la librería estándar).
"""

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".jarvis" / "config.json"

# Valores por defecto pensados para que un fork funcione sin configurar nada.
VAULT_DEFAULT = Path.home() / "Obsidian" / "Vault"
USER_DEFAULT = "tu usuario"
CARPETAS_DEFAULT = ["Finance", "Projects", "Ideas", "Learning", "Prompts", "Weekly"]


def cargar():
    """Devuelve el dict de configuración (vacío si falta o está roto)."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def ruta_vault():
    """Ruta absoluta al vault de Obsidian (configurable en config.json)."""
    valor = cargar().get("vault", str(VAULT_DEFAULT))
    return Path(valor).expanduser()


def nombre_usuario():
    """Nombre del usuario para los system prompts (default genérico)."""
    return cargar().get("user_name", USER_DEFAULT)


def carpetas():
    """Carpetas del vault que Jarvis gestiona."""
    return cargar().get("carpetas", list(CARPETAS_DEFAULT))
