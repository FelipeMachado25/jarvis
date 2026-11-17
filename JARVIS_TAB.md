# 🎙️ Pestaña Jarvis — “Hey Jarvis, ¿qué tengo pendiente?”

Una pestaña en el navegador con voz: le hablas, te contesta en voz alta y te
muestra en tres paneles tus **tareas**, tu **agenda** y tu **correo sin leer**.
Todo corre en tu Mac. Tus correos y tu agenda **nunca se mandan a un modelo en
la nube**: los procesa Mistral en Ollama o [OpenJarvis](#openjarvis-opcional)
en `localhost`.

```bash
python3 runners/web.py          # abre http://localhost:8765
```

## Qué le puedes decir

| Dices | Jarvis hace |
|---|---|
| “Hey Jarvis, ¿qué tengo pendiente?” / “what do I have pendiente?” | Junta tareas vencidas y de hoy + agenda + correos importantes y te lo resume en voz |
| “Buenos días, Jarvis” | Briefing del día (y el digest de OpenJarvis si está corriendo) |
| “Recuérdame pagar la tarjeta mañana” | Crea `- [ ] pagar la tarjeta 📅 <mañana>` en `Inbox.md` del vault |
| “¿Tengo correos importantes?” | Lee tus no leídos (sin marcarlos) y los separa en importantes / personas / promos |
| “¿Qué tengo en la agenda mañana?” | Lee tus calendarios |
| “Analiza mis finanzas” / “¿cómo van mis proyectos?” / “ideas” | Corre los agentes que ya tenías y guarda el análisis en el vault |
| “Busca notas sobre inversión” | Búsqueda instantánea en el vault |
| Cualquier otra cosa | Charla con el modelo local, con tus pendientes como contexto |

Además: clic en el ☐ de una tarea la marca como hecha en la nota original
(`- [x] … ✅ fecha`), y el botón **Wake word** deja la pestaña escuchando hasta
que digas “Jarvis”.

## Configuración (`~/.jarvis/config.json`)

```json
{
  "vault": "~/Obsidian/Vault",
  "user_name": "Felipe",
  "tareas": { "nota_inbox": "Inbox.md" },
  "correo": { "usuario": "tu@gmail.com", "servidor": "imap.gmail.com", "dias": 3, "max": 25 },
  "agenda": { "ics": ["https://calendar.google.com/calendar/ical/.../private-.../basic.ics"], "dias": 7 },
  "openjarvis": { "url": "http://localhost:8000", "usar": "auto" },
  "web": { "puerto": 8765, "wake_word": "jarvis" }
}
```

Todas las secciones son opcionales: lo que no configures simplemente no aparece.

### Tareas
Cualquier `- [ ]` de cualquier nota del vault. Entiende el formato del plugin
**Obsidian Tasks**: `📅 2026-11-20`, `due:2026-11-20`, prioridad `⏫`/`🔼`.

### Correo (Gmail, iCloud, Outlook)
1. Activa la verificación en 2 pasos y crea una **contraseña de aplicación**
   en <https://myaccount.google.com/apppasswords>.
2. Guárdala en el **Llavero de macOS** (nunca en el config):
   ```bash
   security add-generic-password -s jarvis-email -a tu@gmail.com -w
   ```
   (o exporta `JARVIS_EMAIL_PASSWORD` si no usas macOS).
3. Pon tu correo en `correo.usuario`. iCloud: `imap.mail.me.com`. Outlook: `outlook.office365.com`.

Jarvis solo lee encabezados (remitente, asunto, fecha) con `BODY.PEEK`, así
que **no marca nada como leído** y no descarga el cuerpo de tus correos.

### Agenda
Google Calendar → ⚙️ Configuración → tu calendario → **Dirección secreta en
formato iCal** → pégala en `agenda.ics` (puedes poner varias: trabajo,
personal…). También sirve un archivo `.ics` local o un `webcal://` de iCloud.
Trátala como contraseña: quien la tenga ve tu calendario.

### Voz
- **Reconocimiento**: usa el del navegador (Chrome, Edge o Safari). Ojo: en
  Chrome el audio se procesa en servidores de Google. Si quieres que **el audio
  no salga de tu Mac**, corre OpenJarvis con su backend de voz (Whisper local):
  la pestaña lo detecta y cambia sola a “toca para grabar → transcribir local”.
- **Respuesta en voz**: `speechSynthesis` del sistema (en macOS es local). Para
  una voz mejor: Ajustes del Sistema → Accesibilidad → Contenido leído → descarga
  una voz “Mejorada” en español (Jorge, Mónica, Paulina…).
- Atajos: `/` para escribir, `Esc` para callarlo.

### Desde el iPhone
`python3 runners/web.py --lan` imprime una URL con token para abrirla desde el
celular en la misma WiFi. El chat por texto funciona; la voz en iOS requiere
HTTPS (usa un túnel como Tailscale Serve si la quieres).

## OpenJarvis (opcional)

[OpenJarvis](https://github.com/open-jarvis/OpenJarvis) es el framework de
Stanford (Hazy Research + Scaling Intelligence Lab, Apache 2.0) para “Personal
AI, On Personal Devices”. Es mucho más grande que este Jarvis: conectores para
Gmail, Calendar, iMessage, WhatsApp, Apple Health, Notion, Slack, Oura, Strava…,
memoria, agentes con herramientas, morning digest con audio y un servidor
compatible con la API de OpenAI.

Esta pestaña **se engancha a él si está corriendo** y si no, sigue con Ollama:

```bash
curl -fsSL https://open-jarvis.github.io/OpenJarvis/install.sh | bash
jarvis init --preset morning-digest-mac --force
jarvis connect gdrive        # un solo OAuth: Gmail + Calendar + Tasks
jarvis serve                 # http://localhost:8000
python3 runners/web.py       # la pestaña ahora usa OpenJarvis como cerebro
```

Cuando OpenJarvis está activo la pestaña usa:
- `/v1/chat/completions` → la charla libre pasa por su agente (memoria + herramientas)
- `/api/digest` → el briefing incluye su morning digest
- `/v1/speech/transcribe` → la voz se transcribe con Whisper local

Si `jarvis serve` tiene API key, ponla en `openjarvis.api_key`.

## Privacidad, en una tabla

| Dato | Sale de tu Mac | A dónde |
|---|---|---|
| Notas / tareas | No | — |
| Correo | Solo la conexión IMAP a tu proveedor (como cualquier app de correo) | Gmail/iCloud |
| Agenda | Solo la descarga del `.ics` | Google/iCloud |
| Lo que le preguntas | No | Ollama u OpenJarvis en localhost |
| Tu voz | Depende del navegador (Chrome → Google). Con OpenJarvis: no | — |
