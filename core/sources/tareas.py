"""Tareas pendientes: checkboxes ``- [ ]`` en cualquier nota del vault.

Compatible con el plugin Obsidian Tasks: entiende fechas ``📅 2026-11-20``,
``due:2026-11-20`` o ``@2026-11-20`` y prioridades ``⏫ 🔼`` o ``!``.
"""

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from core import config, vault  # noqa: E402

RE_TAREA = re.compile(r"^(\s*)[-*] \[( |x|X)\] (.+)$")
RE_FECHA = re.compile(r"(?:📅|🗓️?|due:|@)\s*(\d{4}-\d{2}-\d{2})")
RE_PRIORIDAD = re.compile(r"⏫|🔺|🔼|(?:^|\s)!(?:\s|$)")
INBOX_DEFAULT = "Inbox.md"


def _parse_linea(linea):
    """Devuelve (hecha, texto) si la línea es una tarea, o None."""
    m = RE_TAREA.match(linea)
    if not m:
        return None
    return m.group(2).lower() == "x", m.group(3).strip()


def _limpiar(texto):
    """Quita marcadores de fecha/prioridad para mostrar la tarea limpia."""
    texto = RE_FECHA.sub("", texto)
    texto = re.sub(r"⏫|🔺|🔼|🔽|⏬", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def pendientes(hoy=None, limite=60):
    """Lista de tareas abiertas, ordenadas: vencidas, hoy, con fecha, resto."""
    hoy = hoy or date.today()
    tareas = []
    raiz = vault.ruta_vault()
    for ruta in vault.listar_notas():
        try:
            lineas = ruta.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for linea in lineas:
            parsed = _parse_linea(linea)
            if not parsed or parsed[0]:
                continue
            texto = parsed[1]
            m = RE_FECHA.search(texto)
            fecha = None
            if m:
                try:
                    fecha = date.fromisoformat(m.group(1))
                except ValueError:
                    fecha = None
            tareas.append(
                {
                    "texto": _limpiar(texto),
                    "original": texto,
                    "nota": str(ruta.relative_to(raiz)),
                    "fecha": fecha.isoformat() if fecha else None,
                    "vencida": bool(fecha and fecha < hoy),
                    "hoy": bool(fecha and fecha == hoy),
                    "prioridad": bool(RE_PRIORIDAD.search(texto)),
                }
            )

    def orden(t):
        if t["vencida"]:
            grupo = 0
        elif t["hoy"]:
            grupo = 1
        elif t["prioridad"]:
            grupo = 2
        elif t["fecha"]:
            grupo = 3
        else:
            grupo = 4
        return (grupo, t["fecha"] or "9999", t["texto"].lower())

    tareas.sort(key=orden)
    return tareas[:limite]


def _ruta_inbox():
    nombre = config.cargar().get("tareas", {}).get("nota_inbox", INBOX_DEFAULT)
    return vault.ruta_vault() / nombre


def agregar(texto, fecha=None):
    """Añade una tarea a la nota Inbox del vault (captura rápida por voz)."""
    texto = " ".join(str(texto).split())
    if not texto:
        raise ValueError("La tarea está vacía")
    linea = "- [ ] %s" % texto
    if fecha:
        linea += " 📅 %s" % fecha
    ruta = _ruta_inbox()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    previo = ruta.read_text(encoding="utf-8") if ruta.exists() else "# Inbox\n\n"
    if previo and not previo.endswith("\n"):
        previo += "\n"
    ruta.write_text(previo + linea + "\n", encoding="utf-8")
    return {"texto": texto, "fecha": fecha, "nota": ruta.name}


def completar(nota, original, hoy=None):
    """Marca como hecha la primera tarea abierta de ``nota`` con ese texto."""
    hoy = hoy or date.today()
    raiz = vault.ruta_vault().resolve()
    ruta = (raiz / nota).resolve()
    if raiz not in ruta.parents or ruta.suffix != ".md" or not ruta.exists():
        raise ValueError("Nota no válida: %s" % nota)
    lineas = ruta.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, linea in enumerate(lineas):
        parsed = _parse_linea(linea.rstrip("\n"))
        if parsed and not parsed[0] and parsed[1] == original:
            fin = "\n" if linea.endswith("\n") else ""
            lineas[i] = (
                linea.rstrip("\n").replace("[ ]", "[x]", 1) + " ✅ %s" % hoy + fin
            )
            ruta.write_text("".join(lineas), encoding="utf-8")
            return True
    return False
