"""Agente semanal: genera el briefing de los domingos.

Ejecuta finance + projects + ideas vía el orquestador, añade actividad
del vault y escribe el briefing en la carpeta Weekly del vault.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import orchestrator, vault  # noqa: E402
from core.config import nombre_usuario  # noqa: E402
from core.model_client import OllamaClient, OllamaNoDisponible  # noqa: E402

SYSTEM = (
    "Eres Jarvis, el asistente personal de %s. Escribes en español, "
    "en markdown, con tono directo y motivador." % nombre_usuario()
)

RESUMEN_PROMPT = """Con estas secciones de análisis de la semana del usuario:

{secciones}

Escribe un resumen ejecutivo de máximo 6 líneas: lo más importante de la
semana y las 3 prioridades de la próxima.
"""


def _actividad_semana():
    """Lista las notas tocadas en los últimos 7 días, por carpeta."""
    lineas = []
    for carpeta in ("Finance", "Projects", "Ideas", "Learning", "Prompts"):
        recientes = vault.notas_recientes(carpeta, dias=7, limite=10)
        if recientes:
            lineas.append(
                "- **%s**: %s" % (carpeta, ", ".join(r.stem for r in recientes))
            )
    return "\n".join(lineas) or "- Sin actividad registrada esta semana."


def run(guardar=True, **_):
    """Genera el briefing semanal completo y lo guarda en Weekly/."""
    orchestrator.LOGGER.info("Generando briefing semanal...")
    secciones = orchestrator.ejecutar_todos(guardar=False)
    cuerpo = "\n\n---\n\n".join(
        "# %s\n\n%s" % (nombre.capitalize(), texto)
        for nombre, texto in secciones.items()
    )
    try:
        resumen = OllamaClient().generate(
            RESUMEN_PROMPT.format(secciones=cuerpo[:6000]), system=SYSTEM
        )
    except OllamaNoDisponible:
        resumen = "_(Resumen no disponible: Ollama no respondió.)_"
    hoy = date.today().isoformat()
    briefing = (
        "# 📋 Briefing semanal — %s\n\n## Resumen ejecutivo\n\n%s\n\n"
        "## Actividad de la semana\n\n%s\n\n---\n\n%s\n"
        % (hoy, resumen, _actividad_semana(), cuerpo)
    )
    if guardar:
        ruta = vault.escribir_nota("Weekly", "%s-weekly-briefing" % hoy, briefing)
        orchestrator.LOGGER.info("Briefing guardado en %s", ruta)
    return briefing
