"""Agenda desde calendarios iCal (.ics) — Google, iCloud, Outlook. Sin dependencias.

En Google Calendar: Configuración → tu calendario → "Dirección secreta en
formato iCal". Pega esa URL (o la ruta a un .ics local) en config.json::

    "agenda": {"ics": ["https://calendar.google.com/calendar/ical/.../basic.ics"]}

Soporta eventos de día completo, horas UTC/TZID y repeticiones comunes
(RRULE DAILY/WEEKLY/MONTHLY/YEARLY con INTERVAL, COUNT, UNTIL, BYDAY, EXDATE).
"""

import sys
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from core import config  # noqa: E402

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

DIAS_ICAL = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _cfg():
    return config.cargar().get("agenda") or {}


def configurado():
    return bool(_cfg().get("ics"))


def _descargar(fuente):
    if fuente.startswith(("http://", "https://", "webcal://")):
        url = fuente.replace("webcal://", "https://", 1)
        req = urllib.request.Request(url, headers={"User-Agent": "jarvis-local"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="ignore")
    return Path(fuente).expanduser().read_text(encoding="utf-8", errors="ignore")


def _desplegar(texto):
    """Une las líneas 'dobladas' del formato iCal (RFC 5545 §3.1)."""
    lineas = []
    for linea in texto.replace("\r\n", "\n").split("\n"):
        if linea[:1] in (" ", "\t") and lineas:
            lineas[-1] += linea[1:]
        else:
            lineas.append(linea)
    return lineas


def _parse_prop(linea):
    nombre_params, _, valor = linea.partition(":")
    partes = nombre_params.split(";")
    params = dict(p.split("=", 1) for p in partes[1:] if "=" in p)
    return partes[0].upper(), params, valor


def _parse_fecha(valor, params):
    """Devuelve (datetime local naive, todo_el_dia)."""
    valor = valor.strip()
    if params.get("VALUE") == "DATE" or len(valor) == 8:
        return (
            datetime.combine(datetime.strptime(valor[:8], "%Y%m%d").date(), time()),
            True,
        )
    dt = datetime.strptime(valor[:15], "%Y%m%dT%H%M%S")
    if valor.endswith("Z"):
        dt = dt.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    elif params.get("TZID") and ZoneInfo is not None:
        try:
            dt = dt.replace(tzinfo=ZoneInfo(params["TZID"])).astimezone()
            dt = dt.replace(tzinfo=None)
        except Exception:
            pass
    return dt, False


def _desescapar(texto):
    return texto.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";").strip()


def parse_ics(texto):
    """Lista de eventos crudos (dicts) de un calendario iCal."""
    eventos, actual = [], None
    for linea in _desplegar(texto):
        if linea == "BEGIN:VEVENT":
            actual = {"exdates": set()}
        elif linea == "END:VEVENT" and actual is not None:
            if "inicio" in actual:
                eventos.append(actual)
            actual = None
        elif actual is not None and ":" in linea:
            nombre, params, valor = _parse_prop(linea)
            if nombre == "DTSTART":
                actual["inicio"], actual["todo_dia"] = _parse_fecha(valor, params)
            elif nombre == "DTEND":
                actual["fin"], _ = _parse_fecha(valor, params)
            elif nombre == "SUMMARY":
                actual["titulo"] = _desescapar(valor)
            elif nombre == "LOCATION":
                actual["lugar"] = _desescapar(valor)
            elif nombre == "RRULE":
                actual["rrule"] = dict(
                    p.split("=", 1) for p in valor.split(";") if "=" in p
                )
            elif nombre == "EXDATE":
                for v in valor.split(","):
                    actual["exdates"].add(_parse_fecha(v, params)[0])
            elif nombre == "STATUS":
                actual["estado"] = valor.upper()
    return eventos


def _sumar_meses(dt, meses):
    m = dt.month - 1 + meses
    anio, mes = dt.year + m // 12, m % 12 + 1
    try:
        return dt.replace(year=anio, month=mes)
    except ValueError:
        return None  # p. ej. 31 en un mes de 30 días: se omite, como hace iCal


def _ocurrencias(ev, desde, hasta):
    """Genera los inicios del evento dentro de [desde, hasta)."""
    inicio = ev["inicio"]
    regla = ev.get("rrule")
    if not regla:
        if desde <= inicio < hasta or (
            ev.get("fin") and inicio < desde < ev["fin"] and ev.get("todo_dia")
        ):
            yield inicio
        return
    freq = regla.get("FREQ", "")
    intervalo = int(regla.get("INTERVAL", "1") or 1)
    cuenta = int(regla["COUNT"]) if "COUNT" in regla else None
    hasta_regla = None
    if "UNTIL" in regla:
        hasta_regla, _ = _parse_fecha(regla["UNTIL"], {})
        if len(regla["UNTIL"]) == 8:
            hasta_regla += timedelta(days=1)
    dias_semana = [
        DIAS_ICAL[d[-2:]]
        for d in regla.get("BYDAY", "").split(",")
        if d[-2:] in DIAS_ICAL
    ]

    def candidatos():
        n = 0
        while True:
            if freq == "DAILY":
                yield inicio + timedelta(days=n * intervalo)
            elif freq == "WEEKLY":
                base = inicio + timedelta(weeks=n * intervalo)
                lunes = base - timedelta(days=base.weekday())
                for d in sorted(dias_semana or [inicio.weekday()]):
                    c = lunes + timedelta(days=d)
                    if c >= inicio:
                        yield c
            elif freq == "MONTHLY":
                c = _sumar_meses(inicio, n * intervalo)
                if c:
                    yield c
            elif freq == "YEARLY":
                c = _sumar_meses(inicio, 12 * n * intervalo)
                if c:
                    yield c
            else:
                yield inicio
                return
            n += 1
            if n > 5000:
                return

    emitidas = 0
    for c in candidatos():
        if hasta_regla and c >= hasta_regla:
            return
        if c >= hasta:
            return
        emitidas += 1
        if cuenta is not None and emitidas > cuenta:
            return
        if c >= desde and c not in ev["exdates"]:
            yield c


def eventos(dias=None, desde=None, textos=None):
    """Eventos de hoy en adelante (``dias`` días), ordenados por hora."""
    c = _cfg()
    dias = dias or int(c.get("dias", 7))
    desde = desde or datetime.combine(date.today(), time())
    hasta = desde + timedelta(days=dias)
    if textos is None:
        fuentes = c.get("ics") or []
        if isinstance(fuentes, str):
            fuentes = [fuentes]
        textos = []
        for f in fuentes:
            try:
                textos.append(_descargar(f))
            except Exception:
                continue
    salida = []
    for texto in textos:
        for ev in parse_ics(texto):
            if ev.get("estado") == "CANCELLED":
                continue
            duracion = (ev["fin"] - ev["inicio"]) if ev.get("fin") else timedelta(0)
            for inicio in _ocurrencias(ev, desde, hasta):
                salida.append(
                    {
                        "titulo": ev.get("titulo", "(sin título)"),
                        "lugar": ev.get("lugar", ""),
                        "inicio": inicio.isoformat(),
                        "fin": (inicio + duracion).isoformat() if duracion else None,
                        "todo_el_dia": ev.get("todo_dia", False),
                    }
                )
    salida.sort(key=lambda e: e["inicio"])
    return salida
