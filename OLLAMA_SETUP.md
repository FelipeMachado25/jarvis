# How Ollama works in Jarvis

## What it is

[Ollama](https://ollama.com) is a local language-model server. It runs as a
Homebrew service on `http://localhost:11434` and serves **Mistral-7B** (4.4 GB,
open source from Mistral AI).

## Architecture

```
runners/*.py ─► agents/*.py ─► core/model_client.py ─► localhost:11434 (Ollama)
                                                          │
                                                          ▼
                                                    mistral:7b (Apple Silicon GPU)
```

- **Zero cloud calls:** all reasoning goes through `model_client.py`, which
  only ever talks to `localhost`.
- **Zero dependencies:** the client uses `urllib` from the standard library.
- **Automatic fallback:** if Ollama isn't responding, the client tries to start
  it (`brew services start ollama` → `ollama serve`). If it still can't, agents
  degrade with a helpful message instead of crashing.

## Configuration

Edit `~/Jarvis/config/ollama.json`:

```json
{
  "endpoint": "localhost:11434",
  "model": "mistral:7b",
  "temperature": 0.7,
  "context_length": 4096,
  "timeout": 120
}
```

- **model** — any Ollama model works. Tested alternatives: `qwen2:7b`
  (stronger reasoning), `neural-chat:7b` (faster). Switch with
  `ollama pull <model>` and edit this file.
- **temperature** — 0.7 is balanced; drop to 0.3 for drier, more literal analysis.
- **context_length** — 4096 tokens; raise it if your notes are long (uses more RAM).

## Useful commands

```bash
ollama list                            # downloaded models
ollama pull mistral:7b                 # (re)download the model
brew services restart ollama           # restart the server
curl http://localhost:11434/api/tags   # is it alive?
```

## Performance (16 GB RAM, Apple Silicon)

- First call after startup: ~5–10s (loads the model into memory)
- Subsequent calls: the model stays warm in RAM for ~5 min
- Generation: ~30–60 tokens/second on the GPU

## Privacy

Your notes never leave the machine: Ollama has no content telemetry and the
model runs offline. You can disconnect Wi-Fi and Jarvis keeps working.
