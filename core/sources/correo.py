"""Correo por IMAP (Gmail, iCloud, Outlook...) — solo lectura, sin dependencias.

Lee los encabezados de los correos NO leídos de los últimos días (nunca los
marca como leídos: usa ``BODY.PEEK``) y los clasifica en importantes,
personas y promociones/newsletters.

La contraseña NUNCA va en config.json. Se busca, en este orden:
1. Variable de entorno ``JARVIS_EMAIL_PASSWORD``.
2. Llavero de macOS: ``security add-generic-password -s jarvis-email -a TU_CORREO -w``
Para Gmail usa una *contraseña de aplicación* (myaccount.google.com/apppasswords).
"""

import email
import imaplib
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from core import config  # noqa: E402

PALABRAS_IMPORTANTES = (
    "factura",
    "pago",
    "vence",
    "vencimiento",
    "cobro",
    "urgente",
    "importante",
    "entrevista",
    "cita",
    "contrato",
    "firma",
    "banco",
    "tarjeta",
    "deadline",
    "invoice",
    "payment",
    "due",
    "urgent",
    "action required",
    "interview",
    "appointment",
    "contract",
    "sign",
    "overdue",
    "reminder",
    "recordatorio",
    "seguridad",
    "security",
    "verify",
    "confirm",
    "reunión",
    "meeting",
)
CABECERAS = "FROM SUBJECT DATE LIST-UNSUBSCRIBE PRECEDENCE"


class CorreoNoConfigurado(RuntimeError):
    """Falta la sección ``correo`` en config.json o la contraseña."""


def _cfg():
    return config.cargar().get("correo") or {}


def configurado():
    c = _cfg()
    return bool(c.get("usuario"))


def _password(usuario):
    if os.environ.get("JARVIS_EMAIL_PASSWORD"):
        return os.environ["JARVIS_EMAIL_PASSWORD"]
    try:
        r = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                "jarvis-email",
                "-a",
                usuario,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    raise CorreoNoConfigurado(
        "Falta la contraseña de aplicación. Guárdala en el Llavero: "
        "security add-generic-password -s jarvis-email -a %s -w" % usuario
    )


def _decodificar(valor):
    if not valor:
        return ""
    try:
        return str(make_header(decode_header(valor))).strip()
    except Exception:
        return str(valor).strip()


def clasificar(remitente, asunto, es_lista):
    """'importante' | 'persona' | 'promo' según heurísticas simples y locales."""
    texto = ("%s %s" % (remitente, asunto)).lower()
    if any(re.search(r"\b%s\b" % re.escape(p), texto) for p in PALABRAS_IMPORTANTES):
        return "importante"
    if es_lista or re.search(r"no-?reply|newsletter|news@|marketing|promo", texto):
        return "promo"
    return "persona"


def no_leidos(dias=None, maximo=None):
    """Lista de correos no leídos recientes (más nuevos primero)."""
    c = _cfg()
    usuario = c.get("usuario")
    if not usuario:
        raise CorreoNoConfigurado("Añade la sección 'correo' a ~/.jarvis/config.json")
    dias = dias or int(c.get("dias", 3))
    maximo = maximo or int(c.get("max", 25))
    servidor = c.get("servidor", "imap.gmail.com")
    desde = (date.today() - timedelta(days=dias)).strftime("%d-%b-%Y")

    imap = imaplib.IMAP4_SSL(servidor, int(c.get("puerto", 993)), timeout=20)
    try:
        imap.login(usuario, _password(usuario))
        imap.select(c.get("carpeta", "INBOX"), readonly=True)
        _, datos = imap.search(None, "UNSEEN", "SINCE", desde)
        ids = (datos[0] or b"").split()[-maximo:]
        correos = []
        for mid in reversed(ids):
            _, partes = imap.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (%s)])" % CABECERAS)
            crudo = next((p[1] for p in partes if isinstance(p, tuple)), b"")
            msg = email.message_from_bytes(crudo)
            nombre, direccion = parseaddr(_decodificar(msg.get("From")))
            asunto = _decodificar(msg.get("Subject")) or "(sin asunto)"
            try:
                fecha = parsedate_to_datetime(msg.get("Date")).isoformat()
            except Exception:
                fecha = None
            es_lista = bool(msg.get("List-Unsubscribe")) or (
                (msg.get("Precedence") or "").lower() in ("bulk", "list")
            )
            correos.append(
                {
                    "de": nombre or direccion,
                    "direccion": direccion,
                    "asunto": asunto,
                    "fecha": fecha,
                    "tipo": clasificar(nombre + " " + direccion, asunto, es_lista),
                }
            )
        return correos
    finally:
        try:
            imap.logout()
        except Exception:
            pass
