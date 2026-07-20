"""Tests de core.vault: escribir, leer, listar y notas recientes."""

import json

from core import config, vault


def _vault_temporal(tmp_path, monkeypatch):
    """Configura un vault temporal y lo devuelve como Path."""
    ruta_config = tmp_path / "config.json"
    ruta_config.write_text(json.dumps({"vault": str(tmp_path / "vault")}))
    monkeypatch.setattr(config, "CONFIG_PATH", ruta_config)
    return tmp_path / "vault"


def test_escribir_y_leer_nota(tmp_path, monkeypatch):
    _vault_temporal(tmp_path, monkeypatch)
    ruta = vault.escribir_nota("Ideas", "primera", "# Hola\ncuerpo")
    assert ruta.exists()
    assert ruta.name == "primera.md"
    assert "Hola" in vault.leer_nota(ruta)


def test_listar_notas_por_carpeta(tmp_path, monkeypatch):
    _vault_temporal(tmp_path, monkeypatch)
    vault.escribir_nota("Ideas", "a", "uno")
    vault.escribir_nota("Ideas", "b", "dos")
    vault.escribir_nota("Finance", "c", "tres")
    assert len(vault.listar_notas("Ideas")) == 2
    assert len(vault.listar_notas()) == 3


def test_listar_ignora_ocultos(tmp_path, monkeypatch):
    base = _vault_temporal(tmp_path, monkeypatch)
    vault.escribir_nota("Ideas", "visible", "x")
    (base / "Ideas" / ".oculta.md").write_text("y")
    nombres = [p.name for p in vault.listar_notas("Ideas")]
    assert nombres == ["visible.md"]


def test_notas_recientes_ordena_por_mtime(tmp_path, monkeypatch):
    _vault_temporal(tmp_path, monkeypatch)
    vieja = vault.escribir_nota("Ideas", "vieja", "x")
    vault.escribir_nota("Ideas", "nueva", "y")
    import os
    import time

    os.utime(vieja, (time.time() - 10 * 86400,) * 2)  # 10 días atrás
    recientes = vault.notas_recientes("Ideas", dias=7)
    assert [p.name for p in recientes] == ["nueva.md"]
