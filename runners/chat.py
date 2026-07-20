#!/usr/bin/env python3
"""Runner de chat interactivo con Mistral-7B (streaming, 100% local).

Uso: python3 ~/Jarvis/runners/chat.py  (Ctrl-C o "salir" para terminar)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import nombre_usuario  # noqa: E402
from core.model_client import OllamaClient, OllamaNoDisponible  # noqa: E402

SYSTEM = (
    "Eres Jarvis, el asistente personal de %s. Responde en español." % nombre_usuario()
)


def main():
    cliente = OllamaClient()
    print("Jarvis (Mistral-7B local). Escribe 'salir' para terminar.\n")
    historia = ""  # contexto simple: concatenamos los últimos turnos
    while True:
        try:
            pregunta = input("Tú > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not pregunta or pregunta.lower() in ("salir", "exit", "quit"):
            break
        prompt = historia + "Usuario: %s\nJarvis:" % pregunta
        print("Jarvis > ", end="", flush=True)
        try:
            respuesta = []
            for trozo in cliente.generate(prompt, system=SYSTEM, stream=True):
                print(trozo, end="", flush=True)
                respuesta.append(trozo)
            print("\n")
            historia += "Usuario: %s\nJarvis: %s\n" % (pregunta, "".join(respuesta))
            historia = historia[-4000:]  # acotamos el contexto
        except OllamaNoDisponible as e:
            print("\n[%s]" % e)


if __name__ == "__main__":
    main()
