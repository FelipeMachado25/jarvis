"""Agente de proyectos: revisa el estado de la carpeta Projects del vault.

Resume avances, detecta proyectos estancados y propone próximos pasos
usando Mistral-7B en local.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault  # noqa: E402
from core.config import nombre_usuario  # noqa: E402
from core.model_client import OllamaClient, OllamaNoDisponible  # noqa: E402

SYSTEM = (
    "Eres el jefe de proyectos personal de %s. Respondes en español, "
    "en markdown, directo y priorizado." % nombre_usuario()
)

PROMPT = """Notas de proyectos del usuario (con fecha de última modificación):

{notas}

Genera un informe con:
## Proyectos activos (y su estado en una línea)
## Proyectos estancados (sin cambios recientes)
## Próximos pasos sugeridos (máx. 5, priorizados)
"""


def run(**_):
    """Devuelve el informe de proyectos en markdown."""
    rutas = vault.listar_notas("Projects")
    if not rutas:
        return (
            "## Proyectos\nNo hay notas en Projects/ todavía. Crea una nota "
            "por proyecto con sus objetivos y estado."
        )
    # Añadimos la fecha de modificación para que el modelo detecte estancados
    bloques = []
    for ruta in rutas[:15]:
        fecha = datetime.fromtimestamp(ruta.stat().st_mtime).date()
        bloques.append(
            "### %s (modificado %s)\n%s"
            % (ruta.stem, fecha, vault.leer_nota(ruta, max_chars=1200))
        )
    corpus = "\n\n".join(bloques)[:6000]
    try:
        return OllamaClient().generate(PROMPT.format(notas=corpus), system=SYSTEM)
    except OllamaNoDisponible as e:
        listado = "\n".join("- %s" % r.stem for r in rutas)
        return "## Proyectos (sin análisis: %s)\n%s" % (e, listado)
