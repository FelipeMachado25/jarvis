"""Cliente para el modelo open source (Mistral-7B) vía Ollama.

Cero dependencias externas: usa solo la librería estándar de Python.
Jarvis nunca llama a APIs en la nube — todo corre en localhost:11434.
"""

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path.home() / "Jarvis" / "config" / "ollama.json"

DEFAULTS = {
    "endpoint": "http://localhost:11434",
    "model": "mistral:7b",
    "temperature": 0.7,
    "context_length": 4096,
    "timeout": 120,
}


class OllamaNoDisponible(RuntimeError):
    """Se lanza cuando Ollama no responde y no se pudo arrancar."""


class OllamaClient:
    """Wrapper mínimo sobre la API HTTP local de Ollama."""

    def __init__(self, config_path=CONFIG_PATH):
        self.config = dict(DEFAULTS)
        try:
            with open(config_path) as f:
                self.config.update(json.load(f))
        except (OSError, json.JSONDecodeError):
            # Si el config falta o está roto seguimos con los defaults
            pass
        endpoint = str(self.config["endpoint"])
        if not endpoint.startswith("http"):
            endpoint = "http://" + endpoint
        self.endpoint = endpoint.rstrip("/")

    # ---------- salud / arranque ----------

    def esta_vivo(self):
        """True si el servidor de Ollama responde."""
        try:
            with urllib.request.urlopen(self.endpoint + "/api/tags", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def asegurar_servidor(self, reintentos=10):
        """Fallback automático: arranca Ollama si no está corriendo."""
        if self.esta_vivo():
            return
        # Intento 1: servicio de Homebrew. Intento 2: binario directo.
        for cmd in (["brew", "services", "start", "ollama"], ["ollama", "serve"]):
            try:
                subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except OSError:
                continue
            for _ in range(reintentos):
                time.sleep(1)
                if self.esta_vivo():
                    return
        raise OllamaNoDisponible(
            "Ollama no responde en %s. Ejecuta: brew services start ollama"
            % self.endpoint
        )

    def modelo_descargado(self):
        """True si el modelo configurado ya está en disco."""
        try:
            with urllib.request.urlopen(self.endpoint + "/api/tags", timeout=5) as r:
                nombres = [m["name"] for m in json.loads(r.read()).get("models", [])]
            base = self.config["model"].split(":")[0]
            return any(n.startswith(base) for n in nombres)
        except Exception:
            return False

    # ---------- generación ----------

    def generate(self, prompt, system="", stream=False):
        """Genera texto con Mistral. Con stream=True devuelve un generador."""
        self.asegurar_servidor()
        payload = {
            "model": self.config["model"],
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": self.config["temperature"],
                "num_ctx": self.config["context_length"],
            },
        }
        if system:
            payload["system"] = system
        req = urllib.request.Request(
            self.endpoint + "/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=self.config["timeout"])
        except urllib.error.URLError as e:
            raise OllamaNoDisponible("Error llamando a Ollama: %s" % e) from e
        if stream:
            return self._stream(resp)
        with resp:
            return json.loads(resp.read())["response"]

    def _stream(self, resp):
        """Itera la respuesta línea a línea (JSONL de Ollama)."""
        with resp:
            for linea in resp:
                if not linea.strip():
                    continue
                trozo = json.loads(linea)
                if trozo.get("response"):
                    yield trozo["response"]
                if trozo.get("done"):
                    break


def call_open_source_model(prompt, system=""):
    """Atajo de una línea para los agentes."""
    return OllamaClient().generate(prompt, system=system)
