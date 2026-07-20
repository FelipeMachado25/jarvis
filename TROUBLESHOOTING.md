# Troubleshooting

Most problems are the local model server not running. Start there.

## First: run the doctor

```bash
python3 ~/Jarvis/doctor.py
```

It checks your vault, config, the Ollama server, and the model in one shot, and
tells you exactly what's missing.

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `OllamaNoDisponible` / "Ollama no responde" | Model server isn't running | `brew services start ollama` |
| "Modelo no encontrado" / model errors | Model not downloaded | `ollama pull mistral:7b` |
| Agents return "No hay notas en …/" | The folder is empty | Add notes to that folder in your vault |
| Weekly briefing didn't run Sunday | Scheduler not installed, or Mac was off | Check `~/.jarvis/logs/scheduler.log`, then `bash ~/Jarvis/automation/install_scheduler.sh` |
| Wrong vault / notes not found | `vault` path in config is wrong | Edit `~/.jarvis/config.json` → `vault` |
| Agent addresses you by the wrong name | `user_name` not set | Edit `~/.jarvis/config.json` → `user_name` |
| First model call is slow (~5–10s) | Model loading into memory | Normal; subsequent calls are fast for ~5 min |

## Is Ollama actually alive?

```bash
curl http://localhost:11434/api/tags     # should return JSON listing models
ollama list                               # models on disk
brew services restart ollama              # nuclear option: restart the server
```

## Checking the scheduled briefing

```bash
# Is the launchd job loaded?
launchctl list | grep jarvis

# What happened on the last scheduled runs?
cat ~/.jarvis/logs/scheduler.log
cat ~/.jarvis/logs/launchd.log

# Reinstall the schedule (also do this after moving the Jarvis folder)
bash ~/Jarvis/automation/install_scheduler.sh
```

## Debug logs

Every run logs to `~/.jarvis/logs/jarvis.log` (agent timings, failures).
Scheduled runs additionally write to `scheduler.log` and `launchd.log`.

```bash
tail -f ~/.jarvis/logs/jarvis.log         # follow live
```

## FAQ

**Does Jarvis need internet?**
No. After the one-time `ollama pull`, everything runs offline. You can turn off
Wi-Fi and it still works.

**Does it send my notes anywhere?**
No. The only network call is to `localhost:11434`. Your notes never leave the
machine.

**Can I use a different model?**
Yes. `ollama pull <model>` then set `"model"` in `config/ollama.json`. Tested
alternatives: `qwen2:7b` (stronger reasoning), `neural-chat:7b` (faster).
See [OLLAMA_SETUP.md](OLLAMA_SETUP.md).

**Does Obsidian need to be open?**
No. Jarvis reads and writes the markdown files directly on disk.

**Will this work on Linux / Windows?**
The agents and `core/` are pure Python and portable. The **automation** scripts
(`launchd`) and the auto-start of Ollama are macOS-specific. On other OSes,
run the runners manually or wire up your own scheduler (`cron`, Task Scheduler).

**I get `No module named core` when running a runner.**
Run the runner with `python3` by its path (e.g.
`python3 ~/Jarvis/runners/search.py "x"`). The runners add the repo root to
`sys.path` themselves; they don't need to be installed.
