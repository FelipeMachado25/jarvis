"""Agente de ideas: evalúa y prioriza las notas de la carpeta Ideas del vault.

Agrupa ideas parecidas, puntúa potencial vs. esfuerzo y sugiere cuál
explorar esta semana. Todo con Mistral-7B en local.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault  # noqa: E402
from core.config import nombre_usuario  # noqa: E402
from core.model_client import OllamaClient, OllamaNoDisponible  # noqa: E402

SYSTEM = (
    "Eres el evaluador de ideas de %s. Respondes en español, en "
    "markdown, con criterio pragmático: impacto alto y esfuerzo bajo primero."
    % nombre_usuario()
)

PROMPT = """Ideas anotadas por el usuario:

{notas}

Genera:
## Top 3 ideas (con impacto/esfuerzo estimado y por qué)
## Ideas que se parecen entre sí (posibles fusiones)
## Idea sugerida para explorar esta semana (una sola, con primer paso concreto)
"""


def run(**_):
    """Devuelve la evaluación de ideas en markdown."""
    rutas = vault.listar_notas("Ideas")
    if not rutas:
        return (
            "## Ideas\nNo hay notas en Ideas/ todavía. Apunta cada idea en "
            "una nota corta y el agente las evaluará."
        )
    corpus = vault.resumen_corpus(rutas[:20], max_por_nota=800)
    try:
        return OllamaClient().generate(PROMPT.format(notas=corpus), system=SYSTEM)
    except OllamaNoDisponible as e:
        listado = "\n".join("- %s" % r.stem for r in rutas)
        return "## Ideas (sin análisis: %s)\n%s" % (e, listado)
