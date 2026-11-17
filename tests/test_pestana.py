"""Tests offline de la pestaña: tareas, agenda iCal, correo e intenciones."""

import json
from datetime import date, datetime, timedelta

from core import asistente, config
from core.sources import agenda, correo, tareas


def _vault(tmp_path, monkeypatch, extra=None):
    cfg = {"vault": str(tmp_path / "vault")}
    cfg.update(extra or {})
    ruta = tmp_path / "config.json"
    ruta.write_text(json.dumps(cfg))
    monkeypatch.setattr(config, "CONFIG_PATH", ruta)
    (tmp_path / "vault").mkdir(exist_ok=True)
    return tmp_path / "vault"


def test_tareas_ordenadas_y_marcadores(tmp_path, monkeypatch):
    base = _vault(tmp_path, monkeypatch)
    hoy = date(2026, 11, 17)
    (base / "Projects").mkdir()
    (base / "Projects" / "app.md").write_text(
        "- [ ] sin fecha\n"
        "- [x] hecha\n"
        "- [ ] pagar tarjeta 📅 2026-11-10\n"
        "- [ ] llamar al banco due:2026-11-17\n"
        "- [ ] importante ⏫\n"
    )
    ts = tareas.pendientes(hoy=hoy)
    assert [t["texto"] for t in ts] == [
        "pagar tarjeta",
        "llamar al banco",
        "importante",
        "sin fecha",
    ]
    assert ts[0]["vencida"] and ts[1]["hoy"] and ts[2]["prioridad"]


def test_agregar_y_completar(tmp_path, monkeypatch):
    base = _vault(tmp_path, monkeypatch)
    tareas.agregar("comprar leche", "2026-11-18")
    texto = (base / "Inbox.md").read_text()
    assert "- [ ] comprar leche 📅 2026-11-18" in texto
    t = tareas.pendientes()[0]
    assert tareas.completar(t["nota"], t["original"], hoy=date(2026, 11, 17))
    assert (
        "- [x] comprar leche 📅 2026-11-18 ✅ 2026-11-17"
        in (base / "Inbox.md").read_text()
    )
    assert tareas.pendientes() == []


def test_completar_no_sale_del_vault(tmp_path, monkeypatch):
    _vault(tmp_path, monkeypatch)
    (tmp_path / "fuera.md").write_text("- [ ] x\n")
    try:
        tareas.completar("../fuera.md", "x")
        assert False, "debió fallar"
    except ValueError:
        pass


ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART:20261117T150000
DTEND:20261117T160000
SUMMARY:Reunión con\\, el equipo
LOCATION:Zoom
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261118
SUMMARY:Cumpleaños mamá
END:VEVENT
BEGIN:VEVENT
DTSTART:20261102T090000
SUMMARY:Gym
RRULE:FREQ=WEEKLY;BYDAY=MO,WE
EXDATE:20261118T090000
END:VEVENT
BEGIN:VEVENT
DTSTART:20261117T200000
SUMMARY:Cancelado
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR
"""


def test_agenda_parse_y_repeticiones():
    desde = datetime(2026, 11, 17)
    evs = agenda.eventos(dias=7, desde=desde, textos=[ICS])
    titulos = [(e["inicio"][:10], e["titulo"]) for e in evs]
    assert ("2026-11-17", "Reunión con, el equipo") in titulos
    assert ("2026-11-18", "Cumpleaños mamá") in titulos
    gym = [d for d, t in titulos if t == "Gym"]
    assert gym == ["2026-11-23"]  # 18 excluido por EXDATE, 23 es lunes
    assert all(t != "Cancelado" for _, t in titulos)


def test_agenda_count_y_daily():
    ics = (
        "BEGIN:VEVENT\nDTSTART:20261115T080000\nSUMMARY:Pastilla\n"
        "RRULE:FREQ=DAILY;COUNT=4\nEND:VEVENT\n"
    )
    evs = agenda.eventos(dias=10, desde=datetime(2026, 11, 17), textos=[ics])
    assert [e["inicio"][:10] for e in evs] == ["2026-11-17", "2026-11-18"]


def test_clasificar_correo():
    assert correo.clasificar("Banco", "Tu factura vence mañana", False) == "importante"
    assert correo.clasificar("Tienda", "50% off hoy", True) == "promo"
    assert correo.clasificar("Ana Pérez", "¿Cenamos el viernes?", False) == "persona"


def test_detectar_intenciones():
    casos = {
        "Hey Jarvis, what do I have pendiente?": "pendientes",
        "Jarvis, ¿qué tengo pendiente hoy?": "pendientes",
        "recuérdame pagar la luz mañana": "recordar",
        "buenos días jarvis": "briefing",
        "¿tengo correos importantes?": "correo",
        "qué tengo en el calendario mañana": "agenda",
        "analiza mis finanzas": "finanzas",
        "busca notas sobre inversión": "buscar",
        "cuéntame un chiste": "charla",
    }
    for frase, esperado in casos.items():
        assert asistente.detectar(frase) == esperado, frase


def test_recordatorio_crea_tarea(tmp_path, monkeypatch):
    base = _vault(tmp_path, monkeypatch)
    r = asistente.responder("Hey Jarvis, recuérdame pagar la tarjeta mañana")
    manana = (date.today() + timedelta(days=1)).isoformat()
    assert r["intencion"] == "recordar"
    assert "- [ ] pagar la tarjeta 📅 %s" % manana in (base / "Inbox.md").read_text()
