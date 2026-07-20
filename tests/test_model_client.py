"""Tests de core.model_client: config, normalización de endpoint, offline.

Todos son offline: no hacen ninguna llamada de red real.
"""

import json

from core.model_client import DEFAULTS, OllamaClient


def test_defaults_cuando_falta_config(tmp_path):
    cliente = OllamaClient(config_path=tmp_path / "no-existe.json")
    assert cliente.config["model"] == DEFAULTS["model"]
    assert cliente.config["temperature"] == DEFAULTS["temperature"]


def test_endpoint_se_normaliza_con_http(tmp_path):
    ruta = tmp_path / "ollama.json"
    ruta.write_text(json.dumps({"endpoint": "localhost:11434"}))
    cliente = OllamaClient(config_path=ruta)
    assert cliente.endpoint == "http://localhost:11434"


def test_endpoint_respeta_https_y_quita_barra(tmp_path):
    ruta = tmp_path / "ollama.json"
    ruta.write_text(json.dumps({"endpoint": "https://mi-host:1234/"}))
    cliente = OllamaClient(config_path=ruta)
    assert cliente.endpoint == "https://mi-host:1234"


def test_config_rota_cae_a_defaults(tmp_path):
    ruta = tmp_path / "ollama.json"
    ruta.write_text("{ roto")
    cliente = OllamaClient(config_path=ruta)
    assert cliente.config["model"] == DEFAULTS["model"]


def test_esta_vivo_es_false_sin_servidor(tmp_path):
    # Puerto improbable → no hay servidor → esta_vivo() debe ser False, sin excepción.
    ruta = tmp_path / "ollama.json"
    ruta.write_text(json.dumps({"endpoint": "http://localhost:59999"}))
    cliente = OllamaClient(config_path=ruta)
    assert cliente.esta_vivo() is False
