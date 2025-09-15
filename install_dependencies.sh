#!/bin/bash
echo "📦 Installation des dépendances Python (mode --user)..."

# Installer les dépendances principales pour l'utilisateur
pip install --user psutil
pip install --user pygments  # Pour la coloration syntaxique
pip install --user requests  # Pour la télémétrie (optionnel)

# Installer les outils de sécurité pour l'utilisateur
pip install --user safety    # Pour l'audit des dépendances Python
# pip install --user pip-audit  # Alternative à safety

echo "✅ Dépendances Python installées pour l'utilisateur!"
