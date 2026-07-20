"""Tests de core.config: lectura de config, defaults y overrides."""

import json

from core import config


def _escribir_config(tmp_path, monkeypatch, data):
    """Apunta core.config a un config.json temporal y devuelve su ruta."""
    ruta = tmp_path / "config.json"
    ruta.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", ruta)
    return ruta


def test_defaults_cuando_no_hay_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "no-existe.json")
    assert config.nombre_usuario() == config.USER_DEFAULT
    assert config.ruta_vault() == config.VAULT_DEFAULT
    assert config.carpetas() == config.CARPETAS_DEFAULT


def test_override_de_vault_y_usuario(tmp_path, monkeypatch):
    _escribir_config(
        tmp_path,
        monkeypatch,
        {
            "vault": "~/MiVault",
            "user_name": "Ada",
        },
    )
    assert config.nombre_usuario() == "Ada"
    assert config.ruta_vault().name == "MiVault"


def test_config_roto_cae_a_defaults(tmp_path, monkeypatch):
    ruta = tmp_path / "config.json"
    ruta.write_text("{ esto no es json", encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", ruta)
    assert config.nombre_usuario() == config.USER_DEFAULT
