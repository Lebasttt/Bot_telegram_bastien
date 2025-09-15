#!/bin/bash
echo "🚀 Démarrage sécurisé de Jules..."

# Charger l'environnement virtuel si exists
if [ -f "jules_env/bin/activate" ]; then
    source jules_env/bin/activate
fi

# Exécuter la vérification de santé
if ! ./health_check.sh; then
    echo "❌ Échec de la vérification de santé"
    exit 1
fi

# Déterminer le mode d'exécution
MODE=${1:-"interactive"}

case $MODE in
    "daemon")
        echo "🔧 Lancement en mode daemon..."
        python -m ai_supervisor.main --daemon
        ;;
    "security-scan")
        echo "🔒 Lancement du scan de sécurité..."
        python -m ai_supervisor.main --scan-for-secrets
        ;;
    "dependency-check")
        echo "📦 Vérification des dépendances..."
        python -m ai_supervisor.main --check-dependencies
        ;;
    "interactive")
        echo "👤 Lancement en mode interactif..."
        python -m ai_supervisor.main
        ;;
    *)
        echo "Usage: $0 [daemon|security-scan|dependency-check|interactive]"
        exit 1
        ;;
esac

echo "✅ Jules a été lancé avec succès!"
