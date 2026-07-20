#!/usr/bin/env python3
"""Ejemplo comentado: cómo construir tu propio agente de Jarvis.

Un agente es un módulo con UNA función `run(**kwargs) -> str` que devuelve
markdown. Eso es todo el "protocolo". Este ejemplo es un rastreador ficticio
de precios cripto que lee notas del vault y las resume con el modelo local.

Para usarlo de verdad:
  1. Copia este archivo a  agents/crypto.py
  2. Copia el runner de abajo a  runners/crypto.py
  3. (Opcional) regístralo en core/orchestrator.py para el briefing semanal
  4. Ejecuta:  python3 ~/Jarvis/runners/crypto.py
"""

import sys
from pathlib import Path

# Los agentes se ejecutan como scripts, así que añadimos la raíz del repo al
# path antes de importar los paquetes locales (por eso los imports van abajo).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import vault  # noqa: E402
from core.config import nombre_usuario  # noqa: E402
from core.model_client import OllamaClient, OllamaNoDisponible  # noqa: E402

# El system prompt se personaliza con el nombre del usuario (de la config).
SYSTEM = (
    "Eres el analista de criptomonedas de %s. Respondes en español, en "
    "markdown, breve y sin inventar precios." % nombre_usuario()
)

PROMPT = """Estas son las notas del usuario sobre cripto:

{notas}

Resume en 3 puntos qué está observando y una sugerencia prudente.
"""


def run(**_) -> str:
    """Interfaz estándar de agente: lee el vault, llama al modelo, devuelve markdown."""
    # 1. Leer datos del vault (aquí reutilizamos la carpeta Ideas como ejemplo).
    rutas = vault.listar_notas("Ideas")
    if not rutas:
        return "## Cripto\nNo hay notas para analizar todavía."

    # 2. Empaquetar las notas en un bloque acotado para el prompt.
    corpus = vault.resumen_corpus(rutas)

    # 3. Llamar al modelo local, con fallback si Ollama no está disponible.
    try:
        return OllamaClient().generate(PROMPT.format(notas=corpus), system=SYSTEM)
    except OllamaNoDisponible as e:
        return "## Cripto (sin análisis: %s)" % e


if __name__ == "__main__":
    # Permite probar el agente directamente: python3 examples/custom_agent_example.py
    print(run())
