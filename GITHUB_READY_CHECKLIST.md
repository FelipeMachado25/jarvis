# GitHub Ready Checklist

Status of this repo for open-source release. Checked = done in this pass.

## Code quality
- [x] Every module and public function has a docstring
- [x] No debug `print()` in library code (runners print intentionally)
- [x] No `TODO`/`FIXME`/commented-out code
- [x] Black formatting applied (line length 88)
- [x] Ruff lint passes (`E`, `F`, `W`, `I`)
- [x] Zero runtime dependencies (standard library only)

## Documentation
- [x] `README.md` — compelling, English, copy-paste quick start
- [x] `ARCHITECTURE.md` — technical deep dive + diagrams
- [x] `CONTRIBUTING.md` — fork, dev setup, add-an-agent guide, code style
- [x] `TROUBLESHOOTING.md` — common issues + FAQ + debug logs
- [x] `ROADMAP.md` — next steps, known limitations, fork ideas
- [x] `OLLAMA_SETUP.md` — model runtime explained (English)

## Examples
- [x] `examples/example_config.json` (keyless — Jarvis has no API keys)
- [x] `examples/example_finance_vault.md`
- [x] `examples/example_projects_vault.md`
- [x] `examples/custom_agent_example.py` (working, lint-clean)

## Project setup
- [x] `.gitignore` covers caches, build artifacts, venvs, logs
- [x] `LICENSE` present (MIT)
- [x] `pyproject.toml` for metadata, dev extras, tooling config
- [x] `requirements.txt` documents the zero-dependency stance
- [x] `tests/` present; 16 offline tests pass
- [x] `.github/workflows/ci.yml` runs tests + lint on push/PR
- [x] Forkable: personalization lives in `~/.jarvis/config.json`, not source

## Safety
- [x] No API keys anywhere (the project is keyless by design)
- [x] No secrets or personal config committed (`~/.jarvis/` is outside the repo)
- [x] Personal name/vault path moved to config, not hardcoded in source

## Media
- [x] `media/DEMO_SCRIPT.md` — followable 2-min shot list
- [x] `media/ARCHITECTURE_DIAGRAM.txt` — ASCII diagram
- [ ] `media/SCREENSHOTS/` — add real screenshots (manual)
- [ ] Demo video recorded and linked in README (manual — see DEMO_SCRIPT.md)

## Before you push (manual steps)
- [ ] Review the diff and the git history
- [ ] Create the GitHub repo
- [ ] `git remote add origin …` and `git push -u origin main`
- [ ] Repo description: "A private, 100% local personal assistant — LLM agents over your Obsidian vault"
- [ ] Topics: `ai`, `automation`, `personal-assistant`, `obsidian`, `ollama`, `mistral`, `local-first`, `privacy`
- [ ] Record the demo video and link it in the README
