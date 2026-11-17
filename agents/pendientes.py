"""Agente de pendientes: "Hey Jarvis, ¿qué tengo pendiente?".

Junta en una sola vista tus tareas del vault, la agenda de hoy/próximos días
y los correos no leídos que importan. Siempre devuelve algo útil aunque el
modelo, el correo o el calendario no estén disponibles.
"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import nombre_usuario  # noqa: E402
from core.model_client import OllamaClient  # noqa: E402
from core.sources import agenda, correo, tareas  # noqa: E402

SYSTEM = (
    "Eres Jarvis, el asistente personal de %s. Hablas en español natural, "
    "cálido y directo, como un buen asistente ejecutivo. Nunca inventas datos "
    "que no estén en el contexto." % nombre_usuario()
)

DIAS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")

PROMPT_HABLADO = """Hoy es {hoy}. Este es el estado del usuario:

{contexto}

Dale un resumen HABLADO de máximo 5 frases: primero lo urgente (vencido, lo de
hoy, correos importantes), luego lo siguiente en la agenda, y termina con UNA
recomendación concreta de qué hacer primero. Sin markdown, sin listas, sin emojis.
"""


def recopilar(con_correo=True, con_agenda=True):
    """Datos estructurados de todas las fuentes, con errores aislados."""
    datos = {"tareas": [], "eventos": [], "correos": [], "avisos": []}
    try:
        datos["tareas"] = tareas.pendientes()
    except Exception as e:
        datos["avisos"].append("Tareas: %s" % e)
    if con_agenda and agenda.configurado():
        try:
            datos["eventos"] = agenda.eventos()
        except Exception as e:
            datos["avisos"].append("Agenda: %s" % e)
    if con_correo and correo.configurado():
        try:
            datos["correos"] = correo.no_leidos()
        except Exception as e:
            datos["avisos"].append("Correo: %s" % e)
    return datos


def _hora(iso):
    return datetime.fromisoformat(iso).strftime("%H:%M")


def _dia(iso):
    d = datetime.fromisoformat(iso).date()
    if d == date.today():
        return "Hoy"
    if (d - date.today()).days == 1:
        return "Mañana"
    return "%s %s" % (DIAS[d.weekday()], d.strftime("%d/%m"))


def markdown(datos):
    """Vista en markdown, sin modelo (instantánea y siempre disponible)."""
    partes = []
    ts = datos["tareas"]
    vencidas = [t for t in ts if t["vencida"]]
    de_hoy = [t for t in ts if t["hoy"]]
    partes.append(
        "## ✅ Tareas (%d abiertas · %d vencidas · %d para hoy)"
        % (len(ts), len(vencidas), len(de_hoy))
    )
    if not ts:
        partes.append(
            "_Nada pendiente en el vault. Dime “recuérdame …” para anotar algo._"
        )
    for t in ts[:15]:
        marca = (
            "🔴"
            if t["vencida"]
            else "🟡" if t["hoy"] else "⏫" if t["prioridad"] else "▫️"
        )
        fecha = " · %s" % t["fecha"] if t["fecha"] else ""
        partes.append("- %s %s _(%s%s)_" % (marca, t["texto"], t["nota"], fecha))

    if datos["eventos"]:
        partes.append("\n## 📅 Agenda")
        for e in datos["eventos"][:12]:
            hora = "todo el día" if e["todo_el_dia"] else _hora(e["inicio"])
            lugar = " · %s" % e["lugar"] if e["lugar"] else ""
            partes.append(
                "- **%s %s** — %s%s" % (_dia(e["inicio"]), hora, e["titulo"], lugar)
            )

    if datos["correos"]:
        imp = [c for c in datos["correos"] if c["tipo"] == "importante"]
        per = [c for c in datos["correos"] if c["tipo"] == "persona"]
        promo = [c for c in datos["correos"] if c["tipo"] == "promo"]
        partes.append(
            "\n## 📬 Correo no leído (%d importantes · %d personas · %d promos)"
            % (len(imp), len(per), len(promo))
        )
        for c in (imp + per)[:12]:
            icono = "❗" if c["tipo"] == "importante" else "👤"
            partes.append("- %s **%s** — %s" % (icono, c["de"], c["asunto"]))

    for aviso in datos["avisos"]:
        partes.append("\n> ⚠️ %s" % aviso)
    return "\n".join(partes)


def _contexto_compacto(datos):
    lineas = []
    for t in datos["tareas"][:20]:
        estado = "VENCIDA " if t["vencida"] else "HOY " if t["hoy"] else ""
        lineas.append("TAREA %s%s %s" % (estado, t["texto"], t["fecha"] or ""))
    for e in datos["eventos"][:10]:
        lineas.append(
            "EVENTO %s %s %s"
            % (
                _dia(e["inicio"]),
                "" if e["todo_el_dia"] else _hora(e["inicio"]),
                e["titulo"],
            )
        )
    for c in datos["correos"]:
        if c["tipo"] != "promo":
            lineas.append(
                "CORREO %s de %s: %s" % (c["tipo"].upper(), c["de"], c["asunto"])
            )
    return "\n".join(lineas) or "Sin tareas, eventos ni correos pendientes."


def resumen_basico(datos):
    """Resumen hablado sin modelo: frases plantilla."""
    ts = datos["tareas"]
    vencidas = sum(t["vencida"] for t in ts)
    hoy = [t for t in ts if t["hoy"]]
    frases = ["Tienes %d tareas abiertas" % len(ts)]
    if vencidas:
        frases[0] += ", %d vencidas" % vencidas
    if hoy:
        frases.append("Para hoy: %s" % ", ".join(t["texto"] for t in hoy[:3]))
    eventos_hoy = [e for e in datos["eventos"] if _dia(e["inicio"]) == "Hoy"]
    if eventos_hoy:
        e = eventos_hoy[0]
        frases.append(
            "En tu agenda hoy hay %d eventos, empezando con %s%s"
            % (
                len(eventos_hoy),
                e["titulo"],
                "" if e["todo_el_dia"] else " a las " + _hora(e["inicio"]),
            )
        )
    imp = [c for c in datos["correos"] if c["tipo"] == "importante"]
    if imp:
        frases.append(
            "Tienes %d correos importantes sin leer, el primero de %s"
            % (len(imp), imp[0]["de"])
        )
    if ts:
        frases.append("Yo empezaría por: %s" % ts[0]["texto"])
    return ". ".join(frases) + "."


def resumen_hablado(datos, cerebro=None):
    """Resumen natural para voz; usa el modelo local y si no, plantilla."""
    prompt = PROMPT_HABLADO.format(
        hoy=date.today().strftime("%A %d/%m/%Y"), contexto=_contexto_compacto(datos)
    )
    try:
        if cerebro is not None:
            return cerebro(prompt, SYSTEM).strip()
        return OllamaClient().generate(prompt, system=SYSTEM).strip()
    except Exception:
        return resumen_basico(datos)


def run(**_):
    """Contrato estándar de agente: devuelve markdown."""
    return "# 📌 Pendientes — %s\n\n%s" % (
        date.today().isoformat(),
        markdown(recopilar()),
    )
