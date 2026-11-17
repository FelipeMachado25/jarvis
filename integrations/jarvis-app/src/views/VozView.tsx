/**
 * JARVIS · Voz — pestaña de asistente por voz para JARVIS.app (Tauri v2 + React).
 *
 * "Hey Jarvis, ¿qué tengo pendiente?" junta en una respuesta hablada:
 *   - Tareas de la app (SQLite: buckets today / inbox)         → get_tasks
 *   - Plan del día, correo por responder/agendar (JARVIS Lite) → get_vault_note("Lite/.hoy.json")
 *   - Resumen natural con tu modelo local de Ollama            → agent_chat (sin herramientas)
 *
 * Solo usa comandos que la app YA tiene, más tres opcionales de voice.rs
 * (voice_say / voice_stop / voice_transcribe) para cuando el WebView no trae
 * reconocimiento de voz. Nada sale de tu Mac salvo lo que ya hacía la app.
 */
import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// ───────────────────────── tipos (mismos campos que usa la app) ─────────────────────────
type Bucket = "inbox" | "today" | "done";
interface Task {
  id: string;
  title: string;
  bucket: Bucket;
  priority?: string | null;
  due_date?: string | null;
  category?: string | null;
  sort_order?: number;
}
interface PlanItem { id?: string; time?: string; title: string; detail?: string; kind?: string }
interface MailItem { from?: string; subject: string; why?: string; url?: string }
interface Hoy {
  date?: string;
  plan?: PlanItem[];
  mail?: { responder?: MailItem[]; agendar?: MailItem[] };
  note?: string;
  training?: { week?: string; phase?: string };
}
interface Msg { who: "user" | "bot"; text: string }
interface Reply { text: string; speak: string; refresh?: boolean; delegate?: string }

export interface VozViewProps {
  /** true cuando la pestaña está visible (para atajos y wake word). */
  active?: boolean;
  /** Mandar una tarea larga al Agente: setPendingPrompt(p); setActiveView("agent"). */
  onDelegate?: (prompt: string) => void;
  /** Recargar el store de tareas de la app después de crear/completar. */
  onTasksChanged?: () => void;
}

// ───────────────────────── utilidades ─────────────────────────
const call = <T,>(cmd: string, args?: Record<string, unknown>) => invoke<T>(cmd, args);
const today = (d = new Date()) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const addDays = (n: number) => { const d = new Date(); d.setDate(d.getDate() + n); return today(d); };
const norm = (s: string) =>
  s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .replace(/^\s*(hey|oye|ok|hola)?\s*,?\s*jarvis\s*[,.:!?]*\s*/, "").trim();
const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
const stripThink = (s: string) => s.replace(/<think>[\s\S]*?<\/think>/g, "").trim();

const INTENTS: [string, RegExp][] = [
  ["remember", /\b(recuerdame|recordarme|anota(me)?|apunta|agrega(r)? (una )?tarea|anade (una )?tarea|remind me( to)?|add (a )?task)\b/],
  ["done", /\b(ya (hice|termine|complete)|marca(r)? como hecha|tacha|i (did|finished)|mark .* done)\b/],
  ["briefing", /\b(buenos dias|good morning|briefing|como (esta|viene) mi dia|my day|resumen del dia)\b/],
  ["mail", /\b(correo|correos|email|emails|mail|inbox|bandeja)\b/],
  ["plan", /\b(agenda|calendario|calendar|plan del dia|reunion|reuniones|meeting|schedule)\b/],
  ["pending", /\b(pendiente|pendientes|pending|to ?do|que tengo|what do i have|que me falta|tareas|tasks)\b/],
  ["delegate", /\b(pidele al agente|dile al agente|agente|investiga|busca en la web|research)\b/],
];
const detect = (t: string) => INTENTS.find(([, re]) => re.test(norm(t)))?.[0] ?? "chat";

function reminderText(original: string) {
  return original
    .replace(/^\s*(hey|oye|ok|hola)?\s*,?\s*jarvis\s*[,.:!?]*\s*/i, "")
    .replace(/^(por favor\s+)?(recu[eé]rdame( que)?|recordarme|an[oó]ta(me)?( que)?|apunta( que)?|agrega(r)? (una )?tarea:?|a[nñ]ade (una )?tarea:?|remind me( to)?|add (a )?task:?)\s*/i, "")
    .replace(/\b(pasado ma[nñ]ana|ma[nñ]ana|hoy|tomorrow|today)\b/gi, "")
    .replace(/\s+/g, " ").trim().replace(/^[.,\s]+|[.,\s]+$/g, "");
}
function relDate(t: string): string | null {
  if (/pasado manana|day after tomorrow/.test(t)) return addDays(2);
  if (/\b(manana|tomorrow)\b/.test(t)) return addDays(1);
  if (/\b(hoy|today|esta noche|tonight)\b/.test(t)) return today();
  return t.match(/\d{4}-\d{2}-\d{2}/)?.[0] ?? null;
}

// ───────────────────────── voz: hablar ─────────────────────────
function pickVoice(lang: string) {
  if (!("speechSynthesis" in window)) return undefined;
  const vs = speechSynthesis.getVoices().filter((v) => v.lang.startsWith(lang.slice(0, 2)));
  return vs.find((v) => /Premium|Enhanced|Mejorad/i.test(v.name)) ??
    vs.find((v) => /Jorge|Diego|Juan|Paulina|Mónica|Monica|Daniel/i.test(v.name)) ?? vs[0];
}
function speak(text: string, muted: boolean, onState: (s: boolean) => void): Promise<void> {
  const clean = text.replace(/[*_`#>]/g, "").trim();
  if (muted || !clean) return Promise.resolve();
  const english = /\b(the|you|your|have|what|and)\b/i.test(clean) && !/[áéíóúñ¿¡]/i.test(clean);
  if ("speechSynthesis" in window && speechSynthesis.getVoices().length) {
    return new Promise((res) => {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(clean);
      u.lang = english ? "en-US" : "es-ES";
      const v = pickVoice(u.lang); if (v) u.voice = v;
      u.rate = 1.05;
      u.onstart = () => onState(true);
      u.onend = u.onerror = () => { onState(false); res(); };
      speechSynthesis.speak(u);
    });
  }
  // Fallback nativo: `say` de macOS vía voice.rs
  onState(true);
  return call("voice_say", { text: clean, lang: english ? "en" : "es" })
    .catch(() => undefined).finally(() => onState(false)) as Promise<void>;
}
function stopSpeaking() {
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  call("voice_stop").catch(() => undefined);
}

// ───────────────────────── voz: escuchar ─────────────────────────
type SR = {
  lang: string; continuous: boolean; interimResults: boolean;
  start(): void; stop(): void; abort(): void;
  onresult: ((e: any) => void) | null; onerror: ((e: any) => void) | null; onend: (() => void) | null;
};
const SRClass: (new () => SR) | undefined =
  (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;

async function blobToB64(b: Blob) {
  const buf = new Uint8Array(await b.arrayBuffer());
  let s = ""; for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode(...buf.subarray(i, i + 0x8000));
  return btoa(s);
}

// ───────────────────────── componente ─────────────────────────
export default function VozView({ active = true, onDelegate, onTasksChanged }: VozViewProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [hoy, setHoy] = useState<Hoy | null>(null);
  const [model, setModel] = useState<string>("qwen3:8b");
  const [ollama, setOllama] = useState<boolean | null>(null);
  const [log, setLog] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [state, setState] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const [status, setStatus] = useState("Toca el núcleo o pulsa espacio");
  const [muted, setMuted] = useState(() => { try { return localStorage.getItem("voz_muted") === "1"; } catch { return false; } });
  const [wake, setWake] = useState(false);
  const history = useRef<{ role: string; content: string }[]>([]);
  const logRef = useRef<HTMLDivElement>(null);
  const busy = useRef(false);

  const refresh = useCallback(async () => {
    const [t, h] = await Promise.all([
      call<Task[]>("get_tasks", { bucket: null }).catch(() => [] as Task[]),
      call<string>("get_vault_note", { path: "Lite/.hoy.json" }).then((r) => JSON.parse(r) as Hoy).catch(() => null),
    ]);
    setTasks(t); setHoy(h);
    return { t, h };
  }, []);

  useEffect(() => {
    refresh();
    call<boolean>("check_ollama").then(setOllama).catch(() => setOllama(false));
    Promise.all([
      call<string | null>("get_setting", { key: "agent_model" }).catch(() => null),
      call<string | null>("get_setting", { key: "ollama_model" }).catch(() => null),
    ]).then(([a, o]) => setModel(a || o || "qwen3:8b"));
    const id = setInterval(refresh, 5 * 60_000);
    return () => clearInterval(id);
  }, [refresh]);

  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight }); }, [log]);

  const open = useMemo(() => tasks.filter((t) => t.bucket !== "done"), [tasks]);
  const todayTasks = open.filter((t) => t.bucket === "today");
  const overdue = open.filter((t) => t.due_date && t.due_date < today());
  const inbox = open.filter((t) => t.bucket === "inbox");
  const replies = hoy?.mail?.responder ?? [];
  const toSchedule = hoy?.mail?.agendar ?? [];
  const nowHHMM = new Date().toTimeString().slice(0, 5);
  const nextPlan = (hoy?.date === today() ? hoy?.plan ?? [] : []).filter((p) => !p.time || p.time >= nowHHMM);

  // ── el modelo local (mismo comando que usa el Agente, sin herramientas) ──
  const llm = useCallback(async (system: string, user: string) => {
    if (!ollama) throw new Error("Ollama no está corriendo");
    const r = await call<{ content: string }>("agent_chat", {
      runId: "voz-" + uid(), model, think: false, tools: [],
      messages: [{ role: "system", content: system }, ...history.current.slice(-8), { role: "user", content: user }],
    });
    return stripThink(r.content || "");
  }, [model, ollama]);

  const context = useCallback((t: Task[], h: Hoy | null) => {
    const L: string[] = [];
    const d = today();
    for (const x of t.filter((x) => x.bucket !== "done").slice(0, 25))
      L.push(`TAREA[${x.bucket}${x.due_date ? " vence " + x.due_date : ""}${x.due_date && x.due_date < d ? " VENCIDA" : ""}${x.priority === "high" ? " ALTA" : ""}] ${x.title}`);
    if (h?.date === d) for (const p of h.plan ?? []) L.push(`PLAN ${p.time ?? ""} ${p.title}`);
    for (const m of h?.mail?.responder ?? []) L.push(`CORREO POR RESPONDER de ${m.from}: ${m.subject}${m.why ? " (" + m.why + ")" : ""}`);
    for (const m of h?.mail?.agendar ?? []) L.push(`CORREO POR AGENDAR de ${m.from}: ${m.subject}`);
    return L.join("\n") || "Sin tareas, plan ni correos pendientes.";
  }, []);

  const SYSTEM = "Eres JARVIS, el asistente personal de Felipe. Hablas en el idioma en que te hablan, natural, cálido y directo, como un asistente ejecutivo. Nunca inventas datos fuera del contexto. Sin markdown, sin listas, sin emojis: tu respuesta se lee en voz alta.";

  const basicSummary = (t: Task[], h: Hoy | null) => {
    const o = t.filter((x) => x.bucket !== "done");
    const td = o.filter((x) => x.bucket === "today");
    const ov = o.filter((x) => x.due_date && x.due_date < today());
    const f: string[] = [`Tienes ${td.length} tareas para hoy y ${o.length - td.length} en la bandeja`];
    if (ov.length) f.push(ov.length === 1 ? `una está vencida: ${ov[0].title}` : `${ov.length} están vencidas, empezando por ${ov[0].title}`);
    const plan = h?.date === today() ? (h.plan ?? []).filter((p) => !p.time || p.time >= nowHHMM) : [];
    if (plan[0]) f.push(`Lo siguiente en tu plan es ${plan[0].title}${plan[0].time ? " a las " + plan[0].time : ""}`);
    const r = h?.mail?.responder ?? [];
    if (r.length) f.push(`Tienes ${r.length} correos por responder, el primero de ${r[0].from ?? "alguien"}`);
    const first = ov[0] ?? td[0];
    if (first) f.push(`Yo empezaría por ${first.title}`);
    return f.join(". ") + ".";
  };

  // ── cerebro de la pestaña ──
  const answer = useCallback(async (text: string): Promise<Reply> => {
    const intent = detect(text);
    const t = norm(text);

    if (intent === "remember") {
      const title = reminderText(text);
      if (!title) return { text: "¿Qué te anoto?", speak: "¿Qué te anoto?" };
      const due = relDate(t);
      await call("create_task", {
        title, bucket: due === today() ? "today" : "inbox", priority: "medium", dueDate: due, category: null,
      });
      const when = due === today() ? " para hoy" : due === addDays(1) ? " para mañana" : due ? ` para el ${due}` : "";
      return { text: `✓ Anotado${when}: **${title}**`, speak: `Listo, anotado${when}: ${title}.`, refresh: true };
    }

    if (intent === "done") {
      const words = t.split(/\s+/).filter((w) => w.length > 3);
      const best = open
        .map((x) => ({ x, score: words.filter((w) => norm(x.title).includes(w)).length }))
        .sort((a, b) => b.score - a.score)[0];
      if (!best || best.score === 0) return { text: "No encontré esa tarea.", speak: "No encontré esa tarea, ¿cuál era?" };
      await call("update_task", {
        id: best.x.id, title: null, bucket: "done", priority: null, dueDate: null, sortOrder: null, category: null,
      });
      return { text: `✓ Hecha: **${best.x.title}**`, speak: `Perfecto, taché ${best.x.title}.`, refresh: true };
    }

    if (intent === "delegate" && onDelegate) {
      onDelegate(text.replace(/^\s*(hey|oye|ok)?\s*,?\s*jarvis\s*[,.:!?]*\s*/i, ""));
      return { text: "Se lo paso al Agente →", speak: "Se lo paso al agente." };
    }

    const { t: ts, h } = await refresh();

    if (intent === "mail") {
      const r = h?.mail?.responder ?? [], a = h?.mail?.agendar ?? [];
      if (!h) return { text: "No hay resumen de JARVIS Lite en el vault todavía.", speak: "Todavía no tengo el resumen de tu correo. Abre Lite para sincronizarlo." };
      const lines = [...r.map((m) => `• **Responder** — ${m.from ?? ""}: ${m.subject}`), ...a.map((m) => `• **Agendar** — ${m.from ?? ""}: ${m.subject}`)];
      const sp = r.length + a.length === 0 ? "Tu correo está bajo control, nada por responder."
        : `Tienes ${r.length} por responder y ${a.length} por agendar. ` + [...r, ...a].slice(0, 3).map((m) => `${m.from ?? "alguien"}, sobre ${m.subject}`).join("; ") + ".";
      return { text: lines.join("\n") || "Nada por responder.", speak: sp };
    }

    if (intent === "plan") {
      const plan = h?.date === today() ? h.plan ?? [] : [];
      if (!plan.length) return { text: "No hay plan del día en Lite.", speak: "No tengo plan para hoy todavía." };
      return {
        text: plan.map((p) => `• **${p.time ?? "—"}** ${p.title}`).join("\n"),
        speak: `Hoy tienes ${plan.length} cosas en el plan. ` + plan.slice(0, 4).map((p) => `${p.time ? "a las " + p.time + ", " : ""}${p.title}`).join("; ") + ".",
      };
    }

    if (intent === "pending" || intent === "briefing") {
      const ctx = context(ts, h);
      let sp: string;
      try {
        sp = await llm(SYSTEM, `Hoy es ${new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" })}, son las ${nowHHMM}.\n\n${ctx}\n\nResume en máximo 5 frases qué tengo pendiente: primero lo vencido y lo de hoy, luego lo siguiente del plan y los correos por responder. Termina con UNA recomendación de por dónde empezar.`);
      } catch { sp = basicSummary(ts, h); }
      const hi = intent === "briefing" ? `${new Date().getHours() < 13 ? "Buenos días" : "Hola"}, Felipe. ` : "";
      return { text: hi + sp, speak: hi + sp };
    }

    // charla libre con contexto
    try {
      const r = await llm(SYSTEM, `Contexto de Felipe (úsalo solo si es relevante):\n${context(ts, h).slice(0, 2500)}\n\n${text}`);
      return { text: r, speak: r };
    } catch (e) {
      return { text: `No tengo el modelo local disponible (${String(e)}). Arranca Ollama o usa la pestaña Agente.`, speak: "No tengo el modelo local disponible ahora mismo." };
    }
  }, [context, llm, onDelegate, open, refresh]);

  const ask = useCallback(async (raw: string) => {
    const text = raw.trim();
    if (!text || busy.current) return;
    busy.current = true;
    setLog((l) => [...l, { who: "user", text }]);
    setState("thinking"); setStatus("Pensando…");
    try {
      const r = await answer(text);
      setLog((l) => [...l, { who: "bot", text: r.text }]);
      history.current = [...history.current, { role: "user", content: text }, { role: "assistant", content: r.speak }].slice(-12);
      if (r.refresh) { await refresh(); onTasksChanged?.(); }
      busy.current = false;
      await speak(r.speak, muted, (s) => setState(s ? "speaking" : "idle"));
    } catch (e) {
      setLog((l) => [...l, { who: "bot", text: "⚠ " + String(e) }]);
    } finally {
      busy.current = false; setState("idle"); setStatus(wake ? "Escuchando… di “Jarvis”" : "Listo");
    }
  }, [answer, muted, onTasksChanged, refresh, wake]);

  // ── escuchar una vez (clic / espacio) ──
  const recorder = useRef<MediaRecorder | null>(null);
  const listenOnce = useCallback(async () => {
    stopSpeaking();
    if (SRClass) {
      const r = new SRClass(); r.lang = "es-ES"; r.interimResults = true; r.continuous = false;
      setState("listening"); setStatus("Te escucho…");
      r.onresult = (e) => {
        const res = e.results[e.results.length - 1];
        setStatus(res[0].transcript);
        if (res.isFinal) ask(res[0].transcript);
      };
      r.onerror = (e) => { setState("idle"); setStatus(e?.error === "not-allowed" ? "Permiso de micrófono denegado" : "No te escuché bien"); };
      r.onend = () => { if (!busy.current) setState("idle"); };
      r.start();
      return;
    }
    // Sin reconocimiento en el WebView: graba y transcribe con Whisper local (voice.rs)
    if (recorder.current) { recorder.current.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = []; const mr = new MediaRecorder(stream); recorder.current = mr;
      mr.ondataavailable = (e) => chunks.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop()); recorder.current = null;
        setState("thinking"); setStatus("Transcribiendo en local…");
        try {
          const b = new Blob(chunks, { type: mr.mimeType });
          const text = await call<string>("voice_transcribe", { audioB64: await blobToB64(b), mime: mr.mimeType });
          ask(text);
        } catch (e) { setState("idle"); setStatus("⚠ " + String(e)); }
      };
      mr.start(); setState("listening"); setStatus("Grabando… toca otra vez para enviar");
    } catch (e) { setStatus("⚠ Micrófono: " + String(e)); }
  }, [ask]);

  // ── wake word "Jarvis" (solo si el WebView soporta reconocimiento continuo) ──
  useEffect(() => {
    if (!wake || !active || !SRClass) return;
    let alive = true, waiting = false, rec: SR | null = null;
    const start = () => {
      if (!alive) return;
      if (busy.current) { setTimeout(start, 800); return; }
      rec = new SRClass!(); rec.lang = "es-ES"; rec.continuous = true; rec.interimResults = true;
      setState("listening"); setStatus("Escuchando… di “Jarvis”");
      rec.onresult = (e) => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const phrase: string = e.results[i][0].transcript; const final = e.results[i].isFinal;
          if (waiting) { if (final && phrase.trim()) { waiting = false; ask(phrase); } continue; }
          const m = phrase.match(/\b(hey|oye|ok|hola)?\s*jarvis\b/i);
          if (!m || !final) continue;
          const rest = phrase.slice((m.index ?? 0) + m[0].length).replace(/^[\s,.:!?]+/, "");
          if (rest.length > 2) ask(rest);
          else { waiting = true; setStatus("¿Sí?"); speak("¿Sí?", muted, () => undefined); setTimeout(() => (waiting = false), 8000); }
        }
      };
      rec.onerror = (e) => { if (e?.error === "not-allowed") { alive = false; setWake(false); setStatus("Permiso de micrófono denegado"); } };
      rec.onend = () => { if (alive) setTimeout(start, 300); };
      try { rec.start(); } catch { /* ya estaba corriendo */ }
    };
    start();
    return () => { alive = false; try { rec?.abort(); } catch { /* */ } setState("idle"); };
  }, [wake, active, ask, muted]);

  // ── atajos: espacio = hablar, Esc = callar ──
  useEffect(() => {
    if (!active) return;
    const h = (e: KeyboardEvent) => {
      const typing = document.activeElement instanceof HTMLInputElement || document.activeElement instanceof HTMLTextAreaElement;
      if (e.code === "Space" && !typing && !e.metaKey) { e.preventDefault(); listenOnce(); }
      if (e.key === "Escape") { stopSpeaking(); setState("idle"); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [active, listenOnce]);

  const completeTask = async (t: Task) => {
    setTasks((ts) => ts.map((x) => (x.id === t.id ? { ...x, bucket: "done" } : x)));
    await call("update_task", { id: t.id, title: null, bucket: "done", priority: null, dueDate: null, sortOrder: null, category: null }).catch(() => refresh());
    onTasksChanged?.();
  };

  // ───────────────────────── UI ─────────────────────────
  const orbAnim = state === "listening" ? "animate-pulse scale-105" : state === "thinking" ? "animate-spin-slow" : state === "speaking" ? "animate-pulse" : "";
  const chip = "font-mono-jb text-[11px] px-3 py-1.5 rounded-full bg-[#141414] border border-[#232323] text-[#bdbdbd] hover:border-[#3d4a1c] hover:text-[#c8f135] transition-colors";
  const card = "rounded-2xl border border-[#1c1c1c] bg-[#0f0f0f]/90 p-5 min-w-0";
  const h3 = "font-mono-jb text-[10px] tracking-[0.18em] text-[#6b6b6b] uppercase";

  return (
    <div className="h-full overflow-hidden bg-[#0a0a0a] text-[#e8e8e8]">
      <style>{`@keyframes vozspin{to{transform:rotate(360deg)}}.animate-spin-slow{animation:vozspin 1.4s linear infinite}`}</style>
      <div className="h-full max-w-[1280px] mx-auto px-7 py-6 grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_340px] gap-5">
        {/* ── centro: núcleo + conversación ── */}
        <div className="flex flex-col min-h-0 gap-4">
          <header className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <p className="font-mono-jb text-[10px] tracking-[0.25em] text-[#c8f135]">J A R V I S · V O Z</p>
              <h1 className="mt-1.5 text-[24px] leading-tight font-semibold text-[#ededed]">¿Qué necesitas, Felipe?</h1>
            </div>
            <div className="flex items-center gap-2">
              <span className={`font-mono-jb text-[10px] px-2.5 py-1 rounded-full border ${ollama ? "text-[#c8f135] border-[#c8f13530] bg-[#c8f13510]" : "text-[#f44f4f] border-[#f44f4f40]"}`}>
                {ollama ? "●" : "○"} {model}
              </span>
              <button onClick={() => setWake((w) => !w)} disabled={!SRClass} title={SRClass ? "" : "Este WebView no soporta escucha continua"}
                className={`font-mono-jb text-[11px] px-3 py-1.5 rounded-md border ${wake ? "border-[#c8f135] text-[#c8f135]" : "border-[#2e2e2e] text-[#aaaaaa]"} disabled:opacity-40`}>
                👂 {wake ? "Escuchando “Jarvis”" : "Wake word"}
              </button>
              <button onClick={() => { const m = !muted; setMuted(m); try { localStorage.setItem("voz_muted", m ? "1" : "0"); } catch { /* */ } if (m) stopSpeaking(); }}
                className="font-mono-jb text-[11px] px-3 py-1.5 rounded-md border border-[#2e2e2e] text-[#aaaaaa]">
                {muted ? "🔇" : "🔊"}
              </button>
            </div>
          </header>

          <div className="flex flex-col items-center py-3">
            <button aria-label="Hablar con JARVIS" onClick={listenOnce}
              className={`relative w-28 h-28 rounded-full transition-transform duration-300 ${orbAnim}`}
              style={{
                background: "radial-gradient(circle, #f6ffd6 0 7%, #c8f135 16%, #c8f13555 38%, transparent 64%)",
                boxShadow: state === "idle" ? "0 0 36px #c8f13540" : "0 0 70px #c8f13590, inset 0 0 30px #c8f13560",
              }}>
              <span className="absolute -inset-3 rounded-full border border-[#c8f13540] border-l-transparent border-r-transparent" style={{ animation: "vozspin 9s linear infinite" }} />
            </button>
            <p className="mt-5 font-mono-jb text-[11px] text-[#7a7a7a] min-h-[16px] text-center">{status}</p>
          </div>

          <div ref={logRef} className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-2.5 pr-1">
            {log.length === 0 && (
              <p className="text-[13px] text-[#5a5a5a] text-center">Pulsa <kbd className="font-mono-jb text-[10px] bg-[#1a1a1a] px-1.5 py-0.5 rounded">espacio</kbd> y di “¿qué tengo pendiente?”, “recuérdame pagar la tarjeta mañana” o “ya hice la propuesta”.</p>
            )}
            {log.map((m, i) => (
              <div key={i} className={`max-w-[88%] rounded-xl px-4 py-2.5 text-[14px] leading-relaxed whitespace-pre-wrap border ${m.who === "user" ? "self-end bg-[#141a08] border-[#2a3510] text-[#e8f5c0]" : "self-start bg-[#131313] border-[#1e1e1e] text-[#e0e0e0]"}`}>
                {m.text.split(/(\*\*[^*]+\*\*)/g).map((p, j) => p.startsWith("**") ? <strong key={j} className="text-[#f0f0f0]">{p.slice(2, -2)}</strong> : p)}
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {[["☀ Briefing", "Buenos días Jarvis"], ["◎ ¿Qué tengo pendiente?", "¿Qué tengo pendiente?"], ["✉ Correo", "¿Qué correos tengo por responder?"], ["◷ Plan de hoy", "¿Qué tengo en el plan de hoy?"]].map(([l, q]) => (
              <button key={l} className={chip} onClick={() => ask(q)}>{l}</button>
            ))}
          </div>
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); const v = input; setInput(""); ask(v); }}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Escríbele o háblale a JARVIS…"
              className="flex-1 bg-[#101010] border border-[#232323] rounded-xl px-4 py-3 text-sm text-[#e8e8e8] placeholder:text-[#555] outline-none focus:border-[#3d4a1c]" />
            <button className="font-mono-jb text-[12px] px-5 rounded-xl bg-[#c8f135] text-[#0d0d0d] font-bold hover:brightness-95">❯</button>
          </form>
        </div>

        {/* ── derecha: lo pendiente, en vivo ── */}
        <aside className="flex flex-col gap-4 min-h-0 overflow-y-auto">
          <section className={card}>
            <div className="flex items-center justify-between mb-3">
              <h3 className={h3}>Hoy</h3>
              <span className="font-mono-jb text-[10px] text-[#555]">{todayTasks.length} hoy · {inbox.length} inbox{overdue.length ? ` · ${overdue.length} vencidas` : ""}</span>
            </div>
            {open.length === 0 ? <p className="text-[13px] text-[#5a5a5a]">Nada pendiente.</p> : (
              <ul className="space-y-1.5">
                {[...overdue, ...todayTasks.filter((t) => !overdue.includes(t)), ...inbox.filter((t) => !overdue.includes(t))].slice(0, 12).map((t) => (
                  <li key={t.id} className="flex items-start gap-2.5 group">
                    <button onClick={() => completeTask(t)} title="Marcar como hecha"
                      className="mt-0.5 w-4 h-4 shrink-0 rounded border border-[#3a3a3a] group-hover:border-[#c8f135] hover:bg-[#c8f13525]" />
                    <div className="min-w-0">
                      <p className={`text-[13px] leading-snug ${t.due_date && t.due_date < today() ? "text-[#ff8a84]" : t.bucket === "today" ? "text-[#ececec]" : "text-[#9a9a9a]"}`}>{t.title}</p>
                      {(t.due_date || t.category) && <p className="font-mono-jb text-[10px] text-[#555]">{[t.category, t.due_date].filter(Boolean).join(" · ")}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={card}>
            <div className="flex items-center justify-between mb-3"><h3 className={h3}>Siguiente en el plan</h3></div>
            {nextPlan.length ? (
              <ol className="space-y-2.5">
                {nextPlan.slice(0, 5).map((p, i) => (
                  <li key={p.id ?? i} className="flex gap-3">
                    <span className="font-mono-jb text-[11px] text-[#c8f135] tabular-nums w-11 shrink-0">{p.time ?? "—"}</span>
                    <span className="text-[13px] text-[#e0e0e0] leading-snug">{p.title}</span>
                  </li>
                ))}
              </ol>
            ) : <p className="text-[13px] text-[#5a5a5a]">{hoy ? "Nada más en el plan de hoy." : "Sin resumen de Lite todavía."}</p>}
          </section>

          <section className={card}>
            <div className="flex items-center justify-between mb-3">
              <h3 className={h3}>Correo</h3>
              <span className="font-mono-jb text-[10px] text-[#555]">{replies.length} responder · {toSchedule.length} agendar</span>
            </div>
            {replies.length + toSchedule.length === 0 ? <p className="text-[13px] text-[#5a5a5a]">Inbox bajo control.</p> : (
              <ul className="space-y-2">
                {[...replies.map((m) => ({ ...m, g: "r" })), ...toSchedule.map((m) => ({ ...m, g: "a" }))].slice(0, 8).map((m, i) => (
                  <li key={i}>
                    <button onClick={() => m.url?.startsWith("https://") && call("open_external", { url: m.url })}
                      className="w-full text-left rounded-xl bg-[#131313] border border-[#1e1e1e] hover:border-[#333] px-3 py-2">
                      <span className={`font-mono-jb text-[9.5px] uppercase ${m.g === "r" ? "text-[#e91e8c]" : "text-[#ff9800]"}`}>{m.g === "r" ? "Responder" : "Agendar"}</span>
                      <span className="font-mono-jb text-[10px] text-[#666] ml-2">{m.from}</span>
                      <p className="text-[13px] text-[#e8e8e8] truncate">{m.subject}</p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
