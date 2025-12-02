# -*- coding: utf-8 -*-
"""
Ce fichier centralise toute la configuration de l'agent.
Modifier les chemins et les paramètres ici plutôt que dans le code source.
"""

import os
from pathlib import Path

# ==============================================================================
# SECTION 1 : CHEMINS DES FICHIERS (Le Foyer de l'Agent)
# ==============================================================================
# Le répertoire principal où l'agent stocke toutes ses informations.
GPT_HOME = Path(os.getenv("GPT_HOME", "/storage/emulated/0/GPT"))

# --- Fonctions pour obtenir les chemins dynamiquement ---
# Cela permet de les modifier pour les tests sans affecter le module à l'import.
def get_config_dir(): return GPT_HOME / ".config"
def get_log_dir(): return GPT_HOME / "logs"
def get_rapports_dir(): return GPT_HOME / "rapports_diagnostic"
def get_web_tools_dir(): return GPT_HOME / "web_tools"
def get_security_dir(): return GPT_HOME / "securite_rapports"
def get_copies_dir(): return GPT_HOME / "copies"

# Fichiers de configuration et de état
def get_channel_file(): return GPT_HOME / "gist_channel"
def get_config_file(): return GPT_HOME / "evolution_config"
def get_state_file(): return GPT_HOME / ".state"
def get_comm_file(): return GPT_HOME / "communication.txt"
def get_test_code_file(): return GPT_HOME / "test_code.py"
def get_backup_code_file(): return GPT_HOME / "source_backup.py"

# Fichiers de journalisation et d'apprentissage
def get_log_file(): return get_log_dir() / "evolution.log"
def get_learning_file(): return GPT_HOME / "learning_patterns.log"
def get_missions_file(): return GPT_HOME / "auto_missions.log"
def get_archive_file(): return GPT_HOME / "archives_complete.log"
def get_permission_solutions_file(): return GPT_HOME / "permission_solutions.log"
def get_url_history_file(): return GPT_HOME / "historique_urls.json"

# Fichier pour la mémoire cognitive structurée
def get_memoire_cognitive_file(): return GPT_HOME / "memoire_cognitive.json"


# ==============================================================================
# SECTION 2 : SECRETS ET CLÉS API
# ==============================================================================
# ATTENTION : C'est une mauvaise pratique de stocker des secrets directement
# dans le code. La méthode sécurisée est d'utiliser des variables d'environnement.
# Pour utiliser une variable d'environnement, exécutez dans votre terminal :
# export GITHUB_TOKEN="votre_vrai_token"
# Ensuite, le script le lira automatiquement.

# Le token GitHub DOIT être fourni via une variable d'environnement pour des raisons de sécurité.
# Exécutez dans votre terminal avant de lancer le script :
# export GITHUB_TOKEN="votre_vrai_token"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    print("ATTENTION: La variable d'environnement GITHUB_TOKEN n'est pas définie. Les appels à l'API GitHub risquent d'échouer.")


# ==============================================================================
# SECTION 3 : PARAMÈTRES DE COMPORTEMENT
# ==============================================================================
# Intervalle de temps (secondes) entre chaque vérification de nouvelles commandes.
DEFAULT_POLL_INTERVAL = 15

# Durée maximale (secondes) d'exécution d'une commande avant d'être interrompue.
COMMAND_TIMEOUT = 300

# Durée (secondes) pendant laquelle une commande qui a échoué est mise en pause
# avant de pouvoir être ré-exécutée.
CACHE_DURATION = 30


# ==============================================================================
# SECTION 4 : SÉCURITÉ (Listes Noires)
# ==============================================================================
# Commandes fondamentales qui sont TOUJOURS interdites.
# Cette liste ne devrait jamais être modifiée par l'agent.
IMMUTABLE_BLACKLIST = (
    "rm ", "unlink ", "mv ", " > ", " >> ",
    "chmod ", "chown ", "chgrp ", "mkfs", "dd if="
)

# La liste noire dynamique est initialisée avec la liste immuable.
# L'agent pourra y ajouter de nouvelles règles apprises, mais ne pourra jamais
# retirer les règles de base.
DYNAMIC_BLACKLIST = list(IMMUTABLE_BLACKLIST)

# ==============================================================================
# SECTION 5 : FONCTION D'INITIALISATION
# ==============================================================================

def setup_environment():
    """
    Crée tous les dossiers nécessaires au bon fonctionnement de l'agent.
    Doit être appelée une seule fois au démarrage de l'application principale.
    """
    dirs_to_create = [
        get_log_dir(), get_rapports_dir(), get_security_dir(), get_copies_dir()
    ]
    for d in dirs_to_create:
        try:
            d.mkdir(exist_ok=True, parents=True)
        except Exception as e:
            # Gère les cas où les permissions sont insuffisantes, même dans l'env final.
            print(f"CRITICAL: Impossible de créer le répertoire {d}: {e}")
            # Dans un vrai scénario, on pourrait vouloir arrêter le script ici.
            # Pour l'instant, on se contente d'afficher une erreur critique.
