#!/bin/bash
echo "💾 Sauvegarde de la configuration..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$TIMESTAMP"

mkdir -p "$BACKUP_DIR"

# Sauvegarder les fichiers critiques
cp config.json "$BACKUP_DIR/"
cp -r logs/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r snapshots/ "$BACKUP_DIR/" 2>/dev/null || true

# Sauvegarder les bases de données
for db in process_history.db network_history.db file_history.db performance_history.db; do
    if [ -f "$db" ]; then
        cp "$db" "$BACKUP_DIR/"
    fi
done

echo "✅ Sauvegarde créée: $BACKUP_DIR"
echo "📦 Taille: $(du -sh "$BACKUP_DIR" | cut -f1)"
