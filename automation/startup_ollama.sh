#!/bin/bash
# Arranca Ollama si no está corriendo y verifica que Mistral esté cargado.
# Se ejecuta antes de cualquier agente (lo llama trigger.sh).

ENDPOINT="http://localhost:11434"
MODEL="mistral:7b"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 1. ¿Servidor vivo?
if ! curl -s --max-time 3 "$ENDPOINT/api/tags" > /dev/null; then
    echo "Ollama no responde; arrancando servicio..."
    brew services start ollama 2>/dev/null || (ollama serve &>/dev/null &)
    for i in $(seq 1 15); do
        sleep 1
        curl -s --max-time 2 "$ENDPOINT/api/tags" > /dev/null && break
    done
fi

if ! curl -s --max-time 3 "$ENDPOINT/api/tags" > /dev/null; then
    echo "ERROR: no se pudo arrancar Ollama." >&2
    exit 1
fi

# 2. ¿Modelo descargado?
if ! curl -s "$ENDPOINT/api/tags" | grep -q "${MODEL%%:*}"; then
    echo "Modelo $MODEL no encontrado; descargando..."
    ollama pull "$MODEL" || { echo "ERROR: pull falló." >&2; exit 1; }
fi

echo "Ollama OK — $MODEL listo."
