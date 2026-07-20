"""Agente de finanzas: analiza las notas de la carpeta Finance del vault.

Lee las notas financieras recientes, se las pasa a Mistral-7B (local)
y escribe un análisis en el propio vault.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault  # noqa: E402
from core.config import nombre_usuario  # noqa: E402
from core.model_client import OllamaClient, OllamaNoDisponible  # noqa: E402

SYSTEM = (
    "Eres el analista financiero personal de %s. Respondes en español, "
    "en markdown, conciso y accionable. No inventes cifras que no estén en "
    "las notas." % nombre_usuario()
)

PROMPT = """Estas son las notas financieras recientes del usuario:

{notas}

Genera un análisis breve con estas secciones:
## Estado general
## Gastos e ingresos destacados
## Alertas
## Recomendaciones (máx. 3)
"""


def run(guardar=True, **_):
    """Analiza Finance/ y (opcionalmente) guarda la nota de análisis."""
    rutas = vault.notas_recientes("Finance", dias=30, limite=15)
    if not rutas:
        return (
            "## Finanzas\nNo hay notas en Finance/ todavía. Añade notas de "
            "gastos, ingresos o presupuestos y vuelve a ejecutar el agente."
        )
    corpus = vault.resumen_corpus(rutas)
    try:
        analisis = OllamaClient().generate(PROMPT.format(notas=corpus), system=SYSTEM)
    except OllamaNoDisponible as e:
        # Fallback: sin modelo devolvemos al menos el inventario de notas
        listado = "\n".join("- %s" % r.name for r in rutas)
        return "## Finanzas (sin análisis: %s)\nNotas encontradas:\n%s" % (e, listado)
    if guardar:
        nombre = "analisis-%s" % date.today().isoformat()
        vault.escribir_nota("Finance", nombre, "# Análisis financiero\n\n" + analisis)
    return analisis
