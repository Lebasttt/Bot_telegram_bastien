#!/bin/bash
echo "🏥 Vérification de santé du système Jules..."

# Vérifier que les fichiers critiques existent
required_files=("config.json" "ai_supervisor/__init__.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Fichier manquant: $file"
        exit 1
    fi
done

# Vérifier les permissions
if [ ! -w "." ]; then
    echo "❌ Permissions d'écriture manquantes sur le répertoire courant"
    exit 1
fi

# Vérifier l'espace disque
disk_usage=$(df . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -gt 90 ]; then
    echo "⚠️  Espace disque faible: $disk_usage% utilisé"
fi

# Vérifier la mémoire disponible
mem_available=$(free -m | awk 'NR==2 {print $7}')
if [ "$mem_available" -lt 100 ]; then
    echo "⚠️  Mémoire disponible faible: ${mem_available}MB"
fi

# Test d'import des modules Python
echo "🔧 Test des imports Python..."
python3 -c "
try:
    from ai_supervisor.core.config import CONFIG
    from ai_supervisor.core.logging import logger
    from ai_supervisor.core.security import jules_safe
    print('✅ Modules core importés avec succès')
except Exception as e:
    print(f'❌ Erreur import core: {e}')
    exit(1)

try:
    from ai_supervisor.db.database import SurveillanceDatabase
    print('✅ Module database importé avec succès')
except Exception as e:
    print(f'❌ Erreur import database: {e}')
    exit(1)

try:
    import psutil
    print('✅ psutil importé avec succès')
except ImportError as e:
    print(f'❌ psutil non installé: {e}')
    exit(1)
"

echo "✅ Vérification de santé terminée - Système opérationnel!"
