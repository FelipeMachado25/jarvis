"""Orquestador de Jarvis: coordina los agentes y centraliza el logging.

Cada agente expone una función `run(**kwargs)` que devuelve texto
markdown. El orquestador los ejecuta con manejo de errores para que
el fallo de un agente nunca tumbe el briefing completo.
"""

import logging
import sys
import time
from pathlib import Path

# Permite importar `core` y `agents` ejecutando desde cualquier directorio
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

LOG_DIR = Path.home() / ".jarvis" / "logs"


def configurar_logging(nombre="jarvis"):
    """Logging a archivo (~/.jarvis/logs) y a consola."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(nombre)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    archivo = logging.FileHandler(LOG_DIR / "jarvis.log")
    archivo.setFormatter(formato)
    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    logger.addHandler(archivo)
    logger.addHandler(consola)
    return logger


LOGGER = configurar_logging()


def _cargar_agentes():
    """Importa los agentes aquí (y no arriba) para evitar ciclos."""
    from agents import document_finder, finance, ideas, projects

    return {
        "document_finder": document_finder,
        "finance": finance,
        "projects": projects,
        "ideas": ideas,
    }


def ejecutar_agente(nombre, **kwargs):
    """Ejecuta un agente por nombre. Devuelve (ok, resultado_markdown)."""
    agentes = _cargar_agentes()
    if nombre not in agentes:
        return False, "Agente desconocido: %s" % nombre
    inicio = time.time()
    try:
        resultado = agentes[nombre].run(**kwargs)
        LOGGER.info("Agente %s OK en %.1fs", nombre, time.time() - inicio)
        return True, resultado
    except Exception as e:  # el fallo de un agente no debe tumbar el resto
        LOGGER.error("Agente %s falló: %s", nombre, e)
        return False, "⚠️ El agente %s falló: %s" % (nombre, e)


def ejecutar_todos(**kwargs):
    """Ejecuta todos los agentes de análisis y devuelve sus secciones."""
    secciones = {}
    for nombre in ("finance", "projects", "ideas"):
        _, resultado = ejecutar_agente(nombre, **kwargs)
        secciones[nombre] = resultado
    return secciones
