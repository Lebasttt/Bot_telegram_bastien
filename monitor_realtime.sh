#!/bin/bash
echo "👁️  Surveillance en temps réel..."

# Vérifier que le daemon est en cours d'exécution
if [ ! -f "logs/ai_debug.pid" ]; then
    echo "❌ Le daemon n'est pas en cours d'exécution"
    exit 1
fi

# Lire le PID
PID=$(cat logs/ai_debug.pid 2>/dev/null)

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ Daemon actif (PID: $PID)"
else
    echo "❌ Le daemon n'est pas en cours d'exécution"
    rm -f logs/ai_debug.pid
    exit 1
fi

# Surveiller les logs en temps réel
echo "📊 Affichage des logs en temps réel (Ctrl+C pour arrêter):"
tail -f logs/ai_debug_log.ndjson | while read line; do
    echo "$line" | python3 -m json.tool 2>/dev/null || echo "$line"
done
