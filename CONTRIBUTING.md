# Contributing to Jarvis

Jarvis is built to be forked and adapted. Whether you want to add a custom
agent for your own workflow or contribute an improvement back, this guide gets
you there.

> A note on language: the **code and model prompts are in Spanish** (that's how
> the project started), while the **docs are in English** for reach. If you
> contribute code, match the surrounding Spanish naming; if you contribute
> docs, English. Either is welcome.

## Fork & run locally

```bash
git clone https://github.com/<you>/jarvis.git ~/Jarvis
python3 ~/Jarvis/doctor.py          # sets up your vault + ~/.jarvis/config.json
```

Then point Jarvis at your own vault and name by editing `~/.jarvis/config.json`
(`vault` and `user_name`). You never need to touch the source to use it.

## Development setup

Jarvis has **zero runtime dependencies**, but tests and linting use a few dev
tools:

```bash
cd ~/Jarvis
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"             # pytest, black, ruff
```

## Running the checks

```bash
pytest -q                # all tests are offline — no Ollama required
ruff check .             # lint
black --check .          # formatting
```

CI runs exactly these on every push and PR (see `.github/workflows/ci.yml`).
Keep all three green.

## How to add a custom agent

An agent is one module with one function. Here's the entire contract:

```python
# agents/crypto.py
"""Agente de ejemplo: precio de criptomonedas anotado en el vault."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault                         # noqa: E402
from core.config import nombre_usuario         # noqa: E402
from core.model_client import OllamaClient, OllamaNoDisponible  # noqa: E402

SYSTEM = "Eres el analista cripto de %s. Respondes en español." % nombre_usuario()


def run(**_) -> str:
    """Interfaz estándar de agente: devuelve markdown."""
    notas = vault.listar_notas("Ideas")
    corpus = vault.resumen_corpus(notas)
    try:
        return OllamaClient().generate("Analiza:\n" + corpus, system=SYSTEM)
    except OllamaNoDisponible as e:
        return "## Cripto (sin análisis: %s)" % e
```

Then add a runner so you can call it:

```python
# runners/crypto.py
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents import crypto  # noqa: E402

if __name__ == "__main__":
    print(crypto.run())
```

To include it in the **weekly briefing**, register it in
`core/orchestrator.py` → `_cargar_agentes()` and add its name to the tuple in
`ejecutar_todos()`.

A full, commented version lives in
[examples/custom_agent_example.py](examples/custom_agent_example.py).

## Code style

- **Formatting:** [Black](https://black.readthedocs.io), line length 88.
- **Linting:** [Ruff](https://docs.astral.sh/ruff/) (rules `E`, `F`, `W`, `I`).
  `E402` is intentionally ignored — runners/agents insert the repo root on
  `sys.path` before importing local packages so they can run as scripts.
- **Docstrings** on every module and public function (Spanish, matching the code).
- **No external dependencies in runtime code.** Standard library only. If you
  think you need a dependency, open an issue first — keeping the dependency
  count at zero is a core design goal.
- **Fail soft.** Handle a missing model or empty folder with a helpful string,
  never an unhandled exception.

## Testing approach

- Tests live in `tests/` and are **100% offline** — they never call Ollama.
- Test pure logic directly (e.g. `document_finder._puntuar`).
- For anything that touches the vault, point `core.config.CONFIG_PATH` at a
  temp `config.json` (see `tests/test_vault.py` for the pattern) so tests run
  against a throwaway vault in `tmp_path`.
- Add a test with every behavior change. Keep the suite fast (<1s total).

## Pull requests

1. Fork, branch, make your change.
2. Ensure `pytest`, `ruff check .`, and `black --check .` all pass.
3. Open a PR describing what and why. Screenshots or sample output help.

Thanks for building on Jarvis. 🤖
