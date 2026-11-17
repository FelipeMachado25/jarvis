"""Puente opcional con OpenJarvis (Stanford Hazy Research / Scaling Intelligence).

OpenJarvis (https://github.com/open-jarvis/OpenJarvis) es un framework
local-first con conectores (Gmail, Calendar, iMessage, Apple Health, Notion,
Slack...), memoria, voz (Whisper local) y un servidor compatible con OpenAI:
``jarvis serve`` → http://localhost:8000.

Si está corriendo, la pestaña de Jarvis lo usa como "cerebro" (chat con
herramientas y memoria, transcripción local de voz, digest matutino). Si no,
todo sigue funcionando con Ollama directo. Solo habla con localhost.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import config  # noqa: E402

URL_DEFAULT = "http://localhost:8000"


class OpenJarvisNoDisponible(RuntimeError):
    pass


def _cfg():
    return config.cargar().get("openjarvis") or {}


def url_base():
    return str(_cfg().get("url", URL_DEFAULT)).rstrip("/")


def activado():
    """'auto' (default) usa OpenJarvis si responde; False lo desactiva."""
    return _cfg().get("usar", "auto") not in (False, "no", "off")


def _peticion(ruta, datos=None, timeout=5, cabeceras=None, crudo=False):
    headers = {"Content-Type": "application/json"}
    clave = _cfg().get("api_key")
    if clave:
        headers["Authorization"] = "Bearer %s" % clave
    headers.update(cabeceras or {})
    cuerpo = None
    if datos is not None:
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos).encode()
    req = urllib.request.Request(url_base() + ruta, data=cuerpo, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            contenido = r.read()
            return contenido if crudo else json.loads(contenido or b"{}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise OpenJarvisNoDisponible(str(e)) from e


def disponible():
    if not activado():
        return False
    try:
        _peticion("/health", timeout=2)
        return True
    except OpenJarvisNoDisponible:
        return False


def chat(mensajes, timeout=180):
    """Chat vía /v1/chat/completions (agente + herramientas + memoria)."""
    datos = {"messages": mensajes, "stream": False}
    modelo = _cfg().get("model")
    if modelo:
        datos["model"] = modelo
    r = _peticion("/v1/chat/completions", datos, timeout=timeout)
    try:
        return r["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise OpenJarvisNoDisponible("Respuesta inesperada: %s" % r) from e


def digest():
    """Último morning digest generado por OpenJarvis (si existe)."""
    return _peticion("/api/digest", timeout=10)


def voz_local_disponible():
    try:
        return bool(_peticion("/v1/speech/health", timeout=2))
    except OpenJarvisNoDisponible:
        return False


def transcribir(cuerpo, content_type):
    """Reenvía audio (multipart) a Whisper local de OpenJarvis."""
    return _peticion(
        "/v1/speech/transcribe",
        cuerpo,
        timeout=120,
        cabeceras={"Content-Type": content_type},
    )


def conectores():
    try:
        return _peticion("/v1/connectors", timeout=3)
    except OpenJarvisNoDisponible:
        return None
