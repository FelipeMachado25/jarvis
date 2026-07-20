#!/bin/bash
# Punto de entrada de las ejecuciones programadas (lo llama launchd).
# Uso: trigger.sh [weekly|finance|projects|ideas]

TAREA="${1:-weekly}"
JARVIS="$HOME/Jarvis"
LOG="$HOME/.jarvis/logs/scheduler.log"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

mkdir -p "$HOME/.jarvis/logs"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') tarea: $TAREA ===" >> "$LOG"

# Primero garantizamos que Ollama + Mistral están listos
bash "$JARVIS/automation/startup_ollama.sh" >> "$LOG" 2>&1 || {
    echo "Abortado: Ollama no disponible." >> "$LOG"
    exit 1
}

python3 "$JARVIS/runners/$TAREA.py" >> "$LOG" 2>&1
echo "=== fin ($?) ===" >> "$LOG"
