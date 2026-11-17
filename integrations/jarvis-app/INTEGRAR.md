# JARVIS · Voz — nueva pestaña para JARVIS.app

Pestaña con voz para tu app de escritorio (Tauri v2 + React). Le dices
**“Hey Jarvis, ¿qué tengo pendiente?”** y te contesta en voz alta juntando:

| Fuente | De dónde lo saca (comandos que tu app **ya tiene**) |
|---|---|
| Tareas `today` / `inbox`, vencidas | `get_tasks` (tu SQLite) |
| Plan del día | `get_vault_note("Lite/.hoy.json")` → `plan` |
| Correo por responder / agendar | `Lite/.hoy.json` → `mail.responder` / `mail.agendar` (lo llena Lite a las 7:00 y 19:15 con tu Gmail) |
| Resumen natural y charla | `agent_chat` con tu modelo de Ollama (`agent_model` / `ollama_model`), sin herramientas |

Además, por voz o por texto:
- **“Recuérdame pagar la luz mañana”** → `create_task` (con fecha; si es para hoy va directo a *Hoy*)
- **“Ya hice lo del banco”** → busca la tarea que más se parece y la mueve a `done`
- **“Pídele al agente que investigue …”** → se lo pasa a la pestaña Agente
- **Wake word** “Jarvis”, **espacio** para hablar, **Esc** para callarlo
- Clic en ☐ marca la tarea como hecha; clic en un correo lo abre

## Archivos

```
src/views/VozView.tsx                 → la pestaña (un solo componente, sin dependencias nuevas)
src-tauri/src/commands/voice.rs       → voz nativa (`say`) y Whisper local (opcional)
src-tauri/Info.plist                  → permisos de micrófono y reconocimiento de voz
```

## Cómo meterla en tu proyecto (5 cambios)

**1. Copia los archivos** a las mismas rutas de tu proyecto. Si tu proyecto
ya tiene `src-tauri/Info.plist`, solo añade las dos claves.

**2. Registra el módulo Rust** en `src-tauri/src/commands/mod.rs`:
```rust
pub mod voice;
```

**3. Registra los comandos** en el `invoke_handler` de `src-tauri/src/lib.rs`
(al lado de `agent_chat`, `get_tasks`, etc.):
```rust
commands::voice::voice_say,
commands::voice::voice_stop,
commands::voice::voice_transcribe,
```

**4. Añádela a la barra lateral** (el array donde están `dashboard`, `agent`,
`brain`, `news`, `lite`, `tasks`, `applications`):
```ts
{ id: "voz", label: "Voz (⌘8)", icon: "◎" },
```

**5. Añádela al mapa de vistas y al atajo** (el componente que tiene
`{1:"dashboard",2:"agent",…,7:"news"}` y el objeto `{dashboard: <…/>, brain: <…/>, …}`):
```tsx
import VozView from "./views/VozView";

// atajos: añade 8
const u = { 1: "dashboard", 2: "agent", 3: "brain", 4: "lite", 5: "tasks", 6: "applications", 7: "news", 8: "voz", ",": "settings", k: "agent", l: "lite", b: "brain" };

// vistas:
voz: (
  <VozView
    active={activeView === "voz"}
    onDelegate={(p) => { setPendingPrompt(p); setActiveView("agent"); }}
    onTasksChanged={() => useTaskStore.getState().loadTasks()}
  />
),
```
(`setPendingPrompt` / `setActiveView` son los de tu store de UI; `loadTasks`
es la acción de tu store de tareas.)

Luego `npm run tauri build` como siempre.

## Voz: cómo funciona dentro de la app

- **Hablar**: usa `speechSynthesis` del WebView; si no está, cae a `say` de
  macOS. Para una voz más natural: Ajustes del Sistema → Accesibilidad →
  Contenido leído → Voz del sistema → descarga una voz *Mejorada/Premium* en
  español (Paulina, Jorge, Mónica…). Puedes fijar la voz de `say` con
  `JARVIS_VOICE_ES` / `JARVIS_VOICE_EN`.
- **Escuchar**: si el WebView de macOS trae reconocimiento de voz, lo usa
  (y se activa el wake word). Si no, el botón graba y transcribe **en tu Mac**
  con Whisper:
  ```bash
  brew install ffmpeg whisper-cpp
  mkdir -p ~/.jarvis/models && curl -L -o ~/.jarvis/models/ggml-base.bin \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin
  ```
  (`ggml-small.bin` o `ggml-large-v3-turbo.bin` entienden mejor el español;
  se elige el más grande que encuentre.)
- La primera vez macOS te pedirá permiso de micrófono: por eso el `Info.plist`.

## Verificado

- `VozView.tsx` compila con TypeScript `strict` y se probó renderizada con
  datos simulados de tu app (crear tarea, tachar tarea, correo, pendientes).
- `voice.rs` compila y pasa su test (decodificación base64); no se pudo
  compilar contra Tauri aquí porque el entorno es Linux sin GTK — compílalo en
  tu Mac con el resto del proyecto.
