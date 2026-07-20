"""Agente buscador de documentos en el vault de Obsidian.

Búsqueda por palabras clave con ranking simple (título > contenido),
puro Python, < 1 segundo. Para búsqueda semántica visual está la app
OMNI (/Applications/Omni.app), que indexa todo el disco localmente.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault  # noqa: E402


def _puntuar(query_terms, titulo, texto):
    """Puntúa una nota: coincidencias en título valen 5x, en cuerpo 1x."""
    puntos = 0
    titulo_l, texto_l = titulo.lower(), texto.lower()
    for termino in query_terms:
        puntos += 5 * titulo_l.count(termino)
        puntos += texto_l.count(termino)
    return puntos


def _extracto(texto, termino, ancho=90):
    """Devuelve un fragmento del texto alrededor de la primera coincidencia."""
    pos = texto.lower().find(termino)
    if pos < 0:
        return texto[:ancho].replace("\n", " ")
    inicio = max(0, pos - ancho // 2)
    return texto[inicio : inicio + ancho].replace("\n", " ")


def buscar(query, top=10):
    """Busca en todas las notas del vault. Devuelve [(ruta, puntos, extracto)]."""
    terminos = [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]
    if not terminos:
        return []
    resultados = []
    for ruta in vault.listar_notas():
        texto = vault.leer_nota(ruta, max_chars=50000)
        puntos = _puntuar(terminos, ruta.stem, texto)
        if puntos > 0:
            resultados.append((ruta, puntos, _extracto(texto, terminos[0])))
    resultados.sort(key=lambda r: r[1], reverse=True)
    return resultados[:top]


def run(query="", top=10, **_):
    """Interfaz estándar de agente: devuelve resultados en markdown."""
    if not query:
        return "Uso: pasa una consulta de búsqueda."
    resultados = buscar(query, top=top)
    if not resultados:
        return "Sin resultados para «%s» en el vault." % query
    lineas = ["## Resultados para «%s»\n" % query]
    for ruta, puntos, extracto in resultados:
        relativa = ruta.relative_to(vault.ruta_vault())
        lineas.append("- **%s** (score %d) — %s" % (relativa, puntos, extracto))
    return "\n".join(lineas)
