# Jarvis Demo Video Script (~2 min)

A followable shot list for a short demo. Record with any screen recorder;
keep the terminal font large. Every command below is real and copy-paste ready.

---

## Clip 1 — Intro (15s)

**On camera / voiceover:**
> "This is Jarvis — a personal assistant that runs 100% on my laptop. It reads
> my Obsidian notes, thinks with a local open-source model, and never sends my
> data to the cloud. No API keys, no monthly bill."

**Show:** the repo README hero section, or the `~/Jarvis` folder in the editor.

---

## Clip 2 — Instant search (25s)

**Terminal:**
```bash
python3 ~/Jarvis/runners/search.py "budget march"
```
**Voiceover:**
> "Search is instant — pure Python keyword ranking across every note, no model
> needed."

**Show:** the ranked results printing in under a second.

---

## Clip 3 — Finance agent (30s)

**Terminal:**
```bash
python3 ~/Jarvis/runners/finance.py
```
**Voiceover:**
> "The finance agent reads my Finance folder, reasons over it with Mistral
> running locally, and writes an analysis back into the vault."

**Show:** the streamed analysis, then open the new note in Obsidian.

---

## Clip 4 — Weekly briefing + architecture (30s)

**Terminal:**
```bash
python3 ~/Jarvis/runners/weekly.py
```
**Voiceover:**
> "Once a week this runs by itself — Sunday at 8pm via launchd — and drops a
> full briefing in my vault: finance, projects, ideas, and what I touched this
> week."

**Show:** the briefing note, then cut to the architecture diagram
(`media/ARCHITECTURE_DIAGRAM.txt` or the one in ARCHITECTURE.md) and trace the
flow: runners → orchestrator → agents → model / vault.

---

## Clip 5 — Why it matters (20s)

**Voiceover:**
> "Local, private, zero dependencies, MIT licensed. Fork it, point it at your
> own vault, add your own agent in about 20 lines. Link's in the description."

**Show:** the GitHub repo page, then the `custom_agent_example.py` file.

---

### Recording tips
- Pre-pull the model (`ollama pull mistral:7b`) so there's no download mid-demo.
- Do a warm-up run before recording so the first model call isn't the slow one.
- Have a few sample notes in `Finance/`, `Projects/`, `Ideas/` so agents have
  something to chew on (see `examples/`).
