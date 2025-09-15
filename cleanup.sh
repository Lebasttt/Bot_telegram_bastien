#!/bin/bash
echo "🧹 Nettoyage du système Jules..."

# Arrêter le daemon s'il est en cours d'exécution
if [ -f "logs/ai_debug.pid" ]; then
    PID=$(cat logs/ai_debug.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "🛑 Arrêt du daemon..."
        kill $PID
        sleep 2
    fi
    rm -f logs/ai_debug.pid
fi

# Nettoyer les vieux logs
echo "🗑️  Nettoyage des anciens logs..."
find logs/ -name "*.log.*" -mtime +7 -delete
find logs/ -name "*.ndjson.*" -mtime +7 -delete
find snapshots/ -name "snapshot_*.json" -mtime +30 -delete

# Nettoyer les fichiers temporaires
echo "🧽 Nettoyage des fichiers temporaires..."
rm -f *.pyc *.pyo __pycache__/*.pyc
rm -rf __pycache__/

echo "✅ Nettoyage terminé!"
