<div align="center">

# 🤖 Jarvis

**A private, 100% local personal assistant — open-source LLM agents that read your Obsidian vault and brief you every week.**

_No cloud. No API keys. No monthly bill. No dependencies._

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Dependencies: none](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](requirements.txt)
[![Runs locally](https://img.shields.io/badge/runs-100%25%20local-8A2BE2.svg)](ARCHITECTURE.md)

</div>

---

## What is Jarvis?

Jarvis is a set of small AI agents that run **entirely on your own machine**. They read the plain-text markdown notes in your [Obsidian](https://obsidian.md) vault, reason over them with a local open-source model ([Mistral-7B](https://mistral.ai) via [Ollama](https://ollama.com)), and write useful analysis back into the vault — a finance review, a project status report, an idea evaluation, and a weekly briefing that generates itself every Sunday.

Everything is local. You can turn off your Wi-Fi and Jarvis keeps working.

## Why it exists

Cloud assistants have three problems for personal data: they cost money per token, they send your private notes to someone else's servers, and they stop working when the vendor changes the deal. Jarvis is the opposite bet:

| | Cloud assistant | **Jarvis** |
|---|---|---|
| Your notes leave your machine | Yes | **Never** |
| Cost | Per-token, monthly | **$0** |
| Works offline | No | **Yes** |
| API keys / accounts | Required | **None** |
| Python dependencies | Many | **Zero (stdlib only)** |

## Features

- 🔍 **Instant vault search** — keyword search across every note, ranked, in under a second.
- 💰 **Finance agent** — reads your `Finance/` notes and writes a concise, actionable review.
- 📊 **Projects agent** — summarizes active projects, flags stalled ones, suggests next steps.
- 💡 **Ideas agent** — scores your ideas by impact vs. effort and picks one to explore this week.
- 📋 **Weekly briefing** — runs all agents, adds vault activity, and saves a Sunday briefing automatically (via macOS `launchd`).
- 💬 **Local chat** — an interactive, streaming chat with Mistral-7B, right in your terminal.
- 🛟 **Graceful fallbacks** — if the model is offline, agents degrade with a useful message instead of crashing.

## Quick start

```bash
# 1. Install the local model runtime and pull the model (one time)
brew install ollama
ollama pull mistral:7b

# 2. Clone Jarvis and run the doctor (creates your vault + config, checks everything)
git clone https://github.com/felipemachado/jarvis.git ~/Jarvis
python3 ~/Jarvis/doctor.py

# 3. Use it
python3 ~/Jarvis/runners/search.py "budget march"
python3 ~/Jarvis/runners/weekly.py
```

That's it — no `pip install`, because there's nothing to install.

## Architecture

```
  You  ──►  runners/*.py        thin CLI entry points
             │
             ▼
          core/orchestrator.py   runs agents, logs, isolates failures
             │
             ▼
          agents/*.py            finance · projects · ideas · weekly · search
             │            │
             │            ▼
             │      core/vault.py         reads/writes ~/Obsidian markdown
             ▼
          core/model_client.py   talks ONLY to localhost:11434
             │
             ▼
          Ollama ──► mistral:7b   (Apple Silicon GPU, fully offline)
```

Full write-up in **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Demo

📹 _Demo video: coming soon_ — see **[media/DEMO_SCRIPT.md](media/DEMO_SCRIPT.md)** for the walkthrough.

## Installation (detailed)

**Requirements:** macOS (Apple Silicon recommended), Python 3.9+, [Homebrew](https://brew.sh), [Obsidian](https://obsidian.md) (optional but recommended).

```bash
# Ollama + model
brew install ollama
brew services start ollama      # keeps the local model server running
ollama pull mistral:7b          # ~4.4 GB, one-time download

# Jarvis
git clone https://github.com/felipemachado/jarvis.git ~/Jarvis
python3 ~/Jarvis/doctor.py       # idempotent: creates vault folders + ~/.jarvis/config.json
```

`doctor.py` is safe to re-run any time; it verifies your vault, config, Ollama server, and model.

## Usage

Every command is just `python3 ~/Jarvis/runners/<name>.py`.

```bash
# Search your notes (instant, no model needed)
python3 ~/Jarvis/runners/search.py "budget march"
```
```
## Results for «budget march»

- **Finance/2026-03-budget.md** (score 14) — March budget: fixed costs 1,240€, ...
```

```bash
# Analyze your finances (reads Finance/, writes an analysis note back to the vault)
python3 ~/Jarvis/runners/finance.py

# Project status report
python3 ~/Jarvis/runners/projects.py

# Idea evaluation & prioritization
python3 ~/Jarvis/runners/ideas.py

# Full weekly briefing (also runs automatically Sundays at 20:00)
python3 ~/Jarvis/runners/weekly.py

# Interactive local chat (streaming)
python3 ~/Jarvis/runners/chat.py
```

### Feeding Jarvis

Agents only know what's in your vault. Suggested routine:

- **`Finance/`** — one note per month with expenses/income, or loose notes.
- **`Projects/`** — one note per project (goal, status, next steps).
- **`Ideas/`** — a short note per idea; the agent prioritizes them.
- **`Weekly/`** — written by Jarvis; don't touch it, just read it on Sunday.

See ready-to-copy templates in **[examples/](examples/)**.

## Configuration

Jarvis reads `~/.jarvis/config.json` (created by `doctor.py`). Make it yours:

```json
{
  "vault": "~/Obsidian/Vault",
  "user_name": "Ada",
  "carpetas": ["Finance", "Projects", "Ideas", "Learning", "Prompts", "Weekly"],
  "briefing_semanal": { "dia": "domingo", "hora": "20:00" },
  "log_level": "INFO"
}
```

- **`vault`** — path to your Obsidian vault.
- **`user_name`** — the agents address you by this name in their prompts.
- The model itself is configured separately in `config/ollama.json` (model, temperature, context length). See **[OLLAMA_SETUP.md](OLLAMA_SETUP.md)**.

## Automation

The weekly briefing runs **every Sunday at 20:00** via `launchd` (macOS-native — survives reboots and sleep). To install or reinstall it:

```bash
bash ~/Jarvis/automation/install_scheduler.sh
```

Scheduled-run logs: `~/.jarvis/logs/scheduler.log`.

## Extending Jarvis

Writing your own agent takes about 20 lines. See **[examples/custom_agent_example.py](examples/custom_agent_example.py)** and the guide in **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## Contributing

Forks and PRs are welcome — this is built to be adapted. Start with **[CONTRIBUTING.md](CONTRIBUTING.md)** for the code style, testing approach, and how to add a custom agent. Ideas for where to take it next: **[ROADMAP.md](ROADMAP.md)**.

Having trouble? **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** covers the common issues.

## License

[MIT](LICENSE) © 2026 Felipe Machado. Fork it, change it, ship it.
