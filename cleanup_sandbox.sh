#!/bin/bash
echo "🧹 Nettoyage du système Jules..."

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
