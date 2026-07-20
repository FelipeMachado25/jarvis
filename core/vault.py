"""Acceso al vault de Obsidian (archivos markdown locales).

Lee y escribe notas markdown sin depender de la app de Obsidian. La ruta
del vault es configurable en ``~/.jarvis/config.json`` (ver ``core.config``).
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import config  # noqa: E402


def ruta_vault():
    """Ruta del vault (delegada a core.config, configurable en config.json)."""
    return config.ruta_vault()


def listar_notas(carpeta=""):
    """Devuelve las rutas de todas las notas .md (opcionalmente de una carpeta)."""
    base = ruta_vault() / carpeta if carpeta else ruta_vault()
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.md") if not p.name.startswith("."))


def leer_nota(ruta, max_chars=8000):
    """Lee una nota con límite de tamaño (para no desbordar el contexto)."""
    try:
        return Path(ruta).read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def notas_recientes(carpeta="", dias=7, limite=20):
    """Notas modificadas en los últimos N días, más recientes primero."""
    ahora = datetime.now().timestamp()
    recientes = [
        p for p in listar_notas(carpeta) if (ahora - p.stat().st_mtime) < dias * 86400
    ]
    recientes.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return recientes[:limite]


def escribir_nota(carpeta, nombre, contenido):
    """Crea o sobrescribe una nota dentro del vault y devuelve su ruta."""
    destino = ruta_vault() / carpeta
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / (nombre if nombre.endswith(".md") else nombre + ".md")
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def resumen_corpus(rutas, max_por_nota=1500, max_total=6000):
    """Concatena varias notas en un solo bloque acotado para el prompt."""
    partes, total = [], 0
    for ruta in rutas:
        texto = leer_nota(ruta, max_chars=max_por_nota)
        if not texto.strip():
            continue
        bloque = "### %s\n%s\n" % (ruta.name, texto)
        if total + len(bloque) > max_total:
            break
        partes.append(bloque)
        total += len(bloque)
    return "\n".join(partes)
