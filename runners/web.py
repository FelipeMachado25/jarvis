#!/usr/bin/env python3
"""Pestaña Jarvis: servidor web local con voz ("Hey Jarvis").

Uso:
    python3 runners/web.py            # abre http://localhost:8765
    python3 runners/web.py --lan      # accesible desde tu iPhone en la misma WiFi
                                      # (pide un token que se imprime al arrancar)

Cero dependencias. Por defecto solo escucha en 127.0.0.1.
"""

import argparse
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from agents import pendientes  # noqa: E402
from core import asistente, config, orchestrator  # noqa: E402
from core import openjarvis_bridge as oj  # noqa: E402
from core.model_client import OllamaClient  # noqa: E402
from core.sources import agenda, correo, tareas  # noqa: E402

HTML = RAIZ / "web" / "index.html"
MAX_CUERPO = 25 * 1024 * 1024
TOKEN = None  # solo se usa en modo --lan


def estado():
    cfg = config.cargar()
    return {
        "usuario": config.nombre_usuario(),
        "vault": config.ruta_vault().exists(),
        "modelo": OllamaClient().esta_vivo(),
        "openjarvis": oj.disponible(),
        "voz_local": oj.voz_local_disponible() if oj.disponible() else False,
        "correo": correo.configurado(),
        "agenda": agenda.configurado(),
        "wake_word": cfg.get("web", {}).get("wake_word", "jarvis"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "Jarvis/1.0"

    def log_message(self, fmt, *args):
        orchestrator.LOGGER.info("web %s", fmt % args)

    # ---------- utilidades ----------
    def _autorizado(self):
        if TOKEN is None:
            return True
        q = parse_qs(urlparse(self.path).query)
        dado = self.headers.get("X-Jarvis-Token") or (q.get("t") or [""])[0]
        return secrets.compare_digest(dado, TOKEN)

    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False, default=str).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _leer(self):
        largo = int(self.headers.get("Content-Length") or 0)
        if largo > MAX_CUERPO:
            raise ValueError("Petición demasiado grande")
        return self.rfile.read(largo) if largo else b""

    def _leer_json(self):
        crudo = self._leer()
        return json.loads(crudo or b"{}")

    # ---------- rutas ----------
    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta in ("/", "/index.html"):
            cuerpo = HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        if not self._autorizado():
            return self._json({"error": "token inválido"}, 401)
        try:
            if ruta == "/api/estado":
                return self._json(estado())
            if ruta == "/api/pendientes":
                datos = pendientes.recopilar()
                return self._json({**datos, "markdown": pendientes.markdown(datos)})
        except Exception as e:
            return self._json({"error": str(e)}, 500)
        self._json({"error": "no encontrado"}, 404)

    def do_POST(self):
        ruta = urlparse(self.path).path
        if not self._autorizado():
            return self._json({"error": "token inválido"}, 401)
        try:
            if ruta == "/api/preguntar":
                d = self._leer_json()
                return self._json(
                    asistente.responder(d.get("texto", ""), d.get("historial"))
                )
            if ruta == "/api/tarea":
                d = self._leer_json()
                return self._json(tareas.agregar(d.get("texto", ""), d.get("fecha")))
            if ruta == "/api/tarea/hecha":
                d = self._leer_json()
                return self._json({"ok": tareas.completar(d["nota"], d["original"])})
            if ruta == "/api/transcribir":
                cuerpo = self._leer()
                tipo = self.headers.get("Content-Type", "")
                return self._json(oj.transcribir(cuerpo, tipo))
        except (ValueError, KeyError) as e:
            return self._json({"error": str(e)}, 400)
        except Exception as e:
            orchestrator.LOGGER.error("web: %s", e)
            return self._json({"error": str(e)}, 500)
        self._json({"error": "no encontrado"}, 404)


def main():
    global TOKEN
    cfg = config.cargar().get("web", {})
    p = argparse.ArgumentParser(description="Pestaña Jarvis con voz")
    p.add_argument("--puerto", type=int, default=int(cfg.get("puerto", 8765)))
    p.add_argument(
        "--lan", action="store_true", help="Escuchar en la red local (requiere token)"
    )
    p.add_argument("--no-abrir", action="store_true", help="No abrir el navegador")
    a = p.parse_args()

    host = "0.0.0.0" if a.lan else "127.0.0.1"
    if a.lan:
        TOKEN = cfg.get("token") or secrets.token_urlsafe(16)
    servidor = ThreadingHTTPServer((host, a.puerto), Handler)
    url = "http://localhost:%d/" % a.puerto
    print("🤖 Jarvis escuchando en %s" % url)
    if TOKEN:
        print(
            "📱 Desde otro dispositivo: http://<IP-de-tu-Mac>:%d/?t=%s"
            % (a.puerto, TOKEN)
        )
        print("   (la voz en iPhone requiere HTTPS; usa el chat por texto o un túnel)")
    if not a.no_abrir:
        threading.Timer(0.8, webbrowser.open, args=[url]).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nHasta luego.")


if __name__ == "__main__":
    main()
