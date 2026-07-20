# Roadmap

Jarvis works today and is used daily. This is where it could go — a mix of
concrete next steps and open ideas for forks. Nothing here is a promise; it's
an invitation.

## Near term

- [ ] **Semantic search agent** — complement keyword search with local
  embeddings (e.g. `nomic-embed-text` via Ollama) so "money worries" finds a
  note about budget stress. Keep it optional and offline.
- [ ] **Config-driven agent registry** — list active agents in
  `~/.jarvis/config.json` instead of editing `orchestrator.py`, so forks can
  enable/disable agents without touching code.
- [ ] **`jarvis` CLI entry point** — a single `jarvis <command>` wrapper over
  the runners, installable via `pip install -e .`.
- [ ] **Per-agent model overrides** — let a heavy agent use a bigger model and
  a quick one use a fast model, set in config.

## Medium term

- [ ] **Learning agent** — periodic summaries of the `Learning/` folder into
  spaced-repetition prompts.
- [ ] **Cross-note linking** — have agents suggest `[[wikilinks]]` between
  related notes they read.
- [ ] **Richer weekly briefing** — trends over time (are projects moving?
  is spend rising?) by reading previous briefings.
- [ ] **Templated note capture** — a runner that scaffolds a new Finance /
  Project / Idea note from a template.

## Known limitations

- **macOS-first.** The agents and `core/` are portable Python, but automation
  (`launchd`) and Ollama auto-start assume macOS. Linux/Windows work manually.
- **Keyword search, not semantic (yet).** `document_finder` is fast and exact
  but doesn't understand synonyms. Semantic search is on the near-term list.
- **Single model at a time.** One model is configured globally; per-agent
  models are planned.
- **Simple chat memory.** `chat.py` keeps a rolling text window, not a real
  conversation store.
- **No test coverage of the model path.** Tests are offline by design; the
  actual generation path is validated manually.

## Ideas for forks

Jarvis is a small, legible base. Good directions to take it:

- A **research agent** that reads a `Sources/` folder and drafts summaries.
- A **journaling coach** over a `Journal/` folder.
- A **home-ops agent** that reads notes about your house/car/subscriptions.
- Swap Obsidian for **any folder of markdown** — nothing is Obsidian-specific
  except the folder convention.
- A **different frontend** — a menubar app, a web UI, a Raycast extension —
  over the same agents.

Have a fork you're proud of? Open an issue and link it — we'll collect them.
