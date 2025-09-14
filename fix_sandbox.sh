#!/bin/bash
# Script pour réparer l'état Git de la sandbox sans la casser.
set -e
echo "--- Vérification et réparation de l'état Git ---"

# On vérifie si 'git status' fonctionne.
if ! git status &> /dev/null; then
    echo "Dépôt Git corrompu ou manquant. Tentative de réparation..."

    # On supprime l'ancien dépôt corrompu
    rm -rf .git

    # On en crée un nouveau, tout propre
    git init

    # On crée un fichier vide pour pouvoir faire un commit
    touch .sandbox_init

    # On ajoute tous les fichiers au nouveau dépôt
    git add -A

    # On configure un utilisateur pour pouvoir commit
    git config user.name "Jules"
    git config user.email "jules@agent.com"

    # On crée le commit initial indispensable
    git commit -m "Réparation Sandbox: Commit Initial"

    echo "--- Dépôt Git réparé avec succès ---"
else
    echo "--- Dépôt Git semble fonctionnel ---"
fi
