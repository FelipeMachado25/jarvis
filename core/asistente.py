"""Cerebro de la pestaña Jarvis: entiende la frase y decide qué hacer.

Detecta la intención (pendientes, correo, agenda, recordatorio, agentes,
búsqueda o charla libre), ejecuta la acción y devuelve un dict con:
``intencion``, ``markdown`` (para la pantalla) y ``hablar`` (para la voz).

El modelo es OpenJarvis si está corriendo en localhost, si no Ollama.
"""

import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents import pendientes  # noqa: E402
from core import openjarvis_bridge as oj  # noqa: E402
from core import orchestrator  # noqa: E402
from core.config import nombre_usuario  # noqa: E402
from core.model_client import OllamaClient, OllamaNoDisponible  # noqa: E402
from core.sources import agenda, correo, tareas  # noqa: E402

SYSTEM = (
    "Eres Jarvis, el asistente personal de %s. Respondes en el idioma en que "
    "te hablan (español o inglés), breve y útil. Si te pasan contexto personal "
    "(tareas, agenda, correo), úsalo y no inventes nada fuera de él." % nombre_usuario()
)

# Orden importa: lo más específico primero.
INTENCIONES = [
    (
        "recordar",
        r"\b(recuerdame|recordarme|anota(me)?|apunta|agrega(r)? (una )?tarea|"
        r"anade (una )?tarea|remind me( to)?|add (a )?task|note that)\b",
    ),
    (
        "briefing",
        r"\b(buenos dias|good morning|briefing|resumen del dia|"
        r"como (esta|viene) mi dia|my day|daily brief|digest)\b",
    ),
    ("semanal", r"\b(semanal|weekly|resumen de la semana)\b"),
    ("correo", r"\b(correo|correos|email|emails|mail|inbox|bandeja)\b"),
    (
        "agenda",
        r"\b(agenda|calendario|calendar|reunion|reuniones|meeting|"
        r"meetings|eventos?|schedule)\b",
    ),
    (
        "pendientes",
        r"\b(pendiente|pendientes|pending|to ?do|que tengo|"
        r"what do i have|que me falta|tareas|tasks)\b",
    ),
    ("finanzas", r"\b(finanzas|finance|dinero|money|gastos|presupuesto|budget)\b"),
    ("proyectos", r"\b(proyectos?|projects?)\b"),
    ("ideas", r"\b(ideas?)\b"),
    ("buscar", r"\b(busca|buscar|encuentra|search|find)\b"),
]


def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    sin_tildes = re.sub(
        r"^\s*(hey|oye|ok|hola)?\s*,?\s*jarvis\s*[,.:!?]*\s*", "", sin_tildes
    )
    return sin_tildes.strip()


def detectar(texto):
    t = normalizar(texto)
    for nombre, patron in INTENCIONES:
        if re.search(patron, t):
            return nombre
    return "charla"


def cerebro(prompt, system=SYSTEM, historial=None):
    """Genera texto con OpenJarvis (si está) o con Ollama local."""
    if oj.disponible():
        mensajes = [{"role": "system", "content": system}]
        mensajes += list(historial or [])[-8:]
        mensajes.append({"role": "user", "content": prompt})
        try:
            return oj.chat(mensajes)
        except oj.OpenJarvisNoDisponible:
            pass
    previo = "".join(
        "%s: %s\n" % ("Usuario" if m["role"] == "user" else "Jarvis", m["content"])
        for m in list(historial or [])[-6:]
    )
    return OllamaClient().generate(previo + prompt, system=system)


def _fecha_relativa(t):
    """Extrae 'mañana', 'hoy', 'pasado mañana' o YYYY-MM-DD de la frase."""
    hoy = date.today()
    if re.search(r"pasado manana|day after tomorrow", t):
        return (hoy + timedelta(days=2)).isoformat()
    if re.search(r"\b(manana|tomorrow)\b", t):
        return (hoy + timedelta(days=1)).isoformat()
    if re.search(r"\b(hoy|today|tonight|esta noche)\b", t):
        return hoy.isoformat()
    m = re.search(r"\d{4}-\d{2}-\d{2}", t)
    return m.group(0) if m else None


def _texto_recordatorio(original):
    t = re.sub(
        r"^\s*(hey|oye|ok|hola)?\s*,?\s*jarvis\s*[,.:!?]*\s*", "", original, flags=re.I
    )
    t = re.sub(
        r"^(por favor\s+)?(recu[eé]rdame( que)?|recordarme|"
        r"an[oó]ta(me)?( que)?|apunta( que)?|"
        r"agrega(r)? (una )?tarea:?|a[nñ]ade (una )?tarea:?|remind me( to)?|"
        r"add (a )?task:?|note that)\s*",
        "",
        t.strip(),
        flags=re.I,
    )
    t = re.sub(
        r"\b(pasado ma[nñ]ana|ma[nñ]ana|hoy|tomorrow|today|day after tomorrow)\b",
        "",
        t,
        flags=re.I,
    )
    return " ".join(t.split()).strip(" .,")


def _hablar_correo(correos):
    if not correos:
        return "No tienes correos sin leer recientes."
    imp = [c for c in correos if c["tipo"] == "importante"]
    per = [c for c in correos if c["tipo"] == "persona"]
    frase = "Tienes %d correos sin leer: %d importantes y %d de personas" % (
        len(correos),
        len(imp),
        len(per),
    )
    destacados = (imp + per)[:3]
    if destacados:
        frase += ". Destaco: " + "; ".join(
            "%s, sobre %s" % (c["de"], c["asunto"]) for c in destacados
        )
    return frase + "."


def responder(texto, historial=None):
    """Punto de entrada único de la pestaña."""
    texto = (texto or "").strip()
    if not texto:
        return {"intencion": "nada", "markdown": "", "hablar": "¿Sí? Te escucho."}
    intencion = detectar(texto)
    t = normalizar(texto)

    if intencion == "recordar":
        contenido = _texto_recordatorio(texto)
        if not contenido:
            return {
                "intencion": intencion,
                "markdown": "",
                "hablar": "¿Qué quieres que te recuerde?",
            }
        fecha = _fecha_relativa(t)
        r = tareas.agregar(contenido, fecha)
        cuando = {
            date.today().isoformat(): " para hoy",
            (date.today() + timedelta(days=1)).isoformat(): " para mañana",
        }.get(fecha, " para el %s" % fecha if fecha else "")
        return {
            "intencion": intencion,
            "markdown": "✅ Anotado en **%s**: %s%s" % (r["nota"], contenido, cuando),
            "hablar": "Listo, anotado%s: %s." % (cuando, contenido),
            "refrescar": True,
        }

    if intencion in ("pendientes", "briefing"):
        datos = pendientes.recopilar()
        md = pendientes.markdown(datos)
        if intencion == "briefing" and oj.disponible():
            try:
                d = oj.digest()
                if d.get("text") or d.get("content"):
                    md += "\n\n## 🎙️ Digest de OpenJarvis\n\n" + (
                        d.get("text") or d.get("content")
                    )
            except oj.OpenJarvisNoDisponible:
                pass
        hablar = pendientes.resumen_hablado(datos, cerebro=lambda p, s: cerebro(p, s))
        saludo = (
            "Buenos días, %s. " % nombre_usuario() if intencion == "briefing" else ""
        )
        return {
            "intencion": intencion,
            "markdown": md,
            "hablar": saludo + hablar,
            "datos": datos,
        }

    if intencion == "correo":
        if not correo.configurado():
            return {
                "intencion": intencion,
                "markdown": "Configura la sección `correo` en `~/.jarvis/config.json` "
                "(ver JARVIS_TAB.md).",
                "hablar": "Todavía no tengo acceso a tu correo. "
                "Te dejé las instrucciones en pantalla.",
            }
        try:
            correos = correo.no_leidos()
        except Exception as e:
            return {
                "intencion": intencion,
                "markdown": "⚠️ %s" % e,
                "hablar": "No pude entrar a tu correo.",
            }
        datos = {"tareas": [], "eventos": [], "correos": correos, "avisos": []}
        return {
            "intencion": intencion,
            "markdown": pendientes.markdown(datos).split("\n", 2)[-1],
            "hablar": _hablar_correo(correos),
        }

    if intencion == "agenda":
        if not agenda.configurado():
            return {
                "intencion": intencion,
                "markdown": "Configura la sección `agenda` en `~/.jarvis/config.json` "
                "(ver JARVIS_TAB.md).",
                "hablar": "Todavía no tengo tu calendario conectado.",
            }
        dias = (
            1
            if re.search(r"\b(hoy|today)\b", t)
            else 2 if re.search(r"\b(manana|tomorrow)\b", t) else 7
        )
        evs = agenda.eventos(dias=dias)
        if re.search(r"\b(manana|tomorrow)\b", t):
            manana = (date.today() + timedelta(days=1)).isoformat()
            evs = [e for e in evs if e["inicio"].startswith(manana)]
        datos = {"tareas": [], "eventos": evs, "correos": [], "avisos": []}
        md = "\n".join(pendientes.markdown(datos).split("\n")[2:]) or "_Agenda libre._"
        if not evs:
            hablar = "No tienes nada en la agenda para ese periodo."
        else:
            hablar = "Tienes %d eventos. " % len(evs) + "; ".join(
                "%s %s" % (pendientes._dia(e["inicio"]).lower(), e["titulo"])
                for e in evs[:4]
            )
        return {"intencion": intencion, "markdown": md, "hablar": hablar + "."}

    agentes = {"finanzas": "finance", "proyectos": "projects", "ideas": "ideas"}
    if intencion in agentes:
        ok, md = orchestrator.ejecutar_agente(agentes[intencion], guardar=True)
        return {
            "intencion": intencion,
            "markdown": md,
            "hablar": (
                "Aquí tienes el análisis de %s. Lo guardé en tu vault." % intencion
                if ok
                else "El agente de %s falló." % intencion
            ),
        }

    if intencion == "semanal":
        from agents import weekly

        md = weekly.run(guardar=True)
        return {
            "intencion": intencion,
            "markdown": md,
            "hablar": "Tu briefing semanal está listo y guardado en Weekly.",
        }

    if intencion == "buscar":
        consulta = re.sub(
            r"^.*?\b(busca|buscar|encuentra|search|find)\b"
            r"\s*(notas? (de|sobre)|about)?",
            "",
            t,
        ).strip()
        ok, md = orchestrator.ejecutar_agente("document_finder", query=consulta)
        return {
            "intencion": intencion,
            "markdown": md,
            "hablar": "Esto encontré sobre %s." % consulta,
        }

    # Charla libre con un poco de contexto personal
    datos = pendientes.recopilar(con_correo=False)
    contexto = pendientes._contexto_compacto(datos)
    prompt = "Contexto del usuario (solo si es relevante):\n%s\n\nPregunta: %s" % (
        contexto[:2500],
        texto,
    )
    try:
        respuesta = cerebro(prompt, historial=historial)
    except (OllamaNoDisponible, oj.OpenJarvisNoDisponible) as e:
        respuesta = (
            "No tengo modelo disponible ahora mismo (%s). Arranca Ollama con: "
            "`brew services start ollama`" % e
        )
    return {"intencion": "charla", "markdown": respuesta, "hablar": respuesta}
