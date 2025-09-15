#!/bin/bash
echo "🔍 Vérification des prérequis système..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 n'est pas installé"
    exit 1
else
    echo "✅ Python3: $(python3 --version)"
fi

# Vérifier pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 n'est pas installé"
    exit 1
else
    echo "✅ pip3: $(pip3 --version)"
fi

# Vérifier les outils système
for tool in git psutil; do
    if python3 -c "import $tool" 2>/dev/null; then
        echo "✅ $tool: Installé"
    else
        echo "⚠️  $tool: Non installé (sera installé automatiquement)"
    fi
done

echo "✅ Tous les prérequis système sont satisfaits!"
