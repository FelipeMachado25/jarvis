"""Tests del agente de búsqueda (document_finder): puntuación y ranking."""

import json

from agents import document_finder
from core import config


def _vault_con_notas(tmp_path, monkeypatch, notas):
    ruta_config = tmp_path / "config.json"
    ruta_config.write_text(json.dumps({"vault": str(tmp_path / "vault")}))
    monkeypatch.setattr(config, "CONFIG_PATH", ruta_config)
    from core import vault

    for carpeta, nombre, texto in notas:
        vault.escribir_nota(carpeta, nombre, texto)


def test_puntuar_titulo_pesa_mas_que_cuerpo():
    # "presupuesto" en el título (5x) vs. una vez en el cuerpo (1x)
    en_titulo = document_finder._puntuar(["presupuesto"], "presupuesto", "nada")
    en_cuerpo = document_finder._puntuar(["presupuesto"], "otro", "presupuesto")
    assert en_titulo == 5
    assert en_cuerpo == 1


def test_buscar_rankea_por_relevancia(tmp_path, monkeypatch):
    _vault_con_notas(
        tmp_path,
        monkeypatch,
        [
            ("Finance", "presupuesto-marzo", "gastos del mes"),
            ("Ideas", "otra", "una idea sobre presupuesto marginal"),
        ],
    )
    resultados = document_finder.buscar("presupuesto")
    assert resultados
    # La nota con "presupuesto" en el título debe ir primera.
    assert resultados[0][0].stem == "presupuesto-marzo"


def test_buscar_sin_resultados(tmp_path, monkeypatch):
    _vault_con_notas(tmp_path, monkeypatch, [("Ideas", "a", "contenido")])
    assert document_finder.buscar("xyzinexistente") == []


def test_query_vacia_no_rompe(tmp_path, monkeypatch):
    _vault_con_notas(tmp_path, monkeypatch, [("Ideas", "a", "x")])
    assert document_finder.buscar("") == []
