# -*- coding: utf-8 -*-
"""
Module de journalisation centralisé pour l'agent.
Tous les autres modules utiliseront ce service pour enregistrer leurs actions.
"""

from datetime import datetime
from . import config

def log(message: str):
    """
    Écrit un message horodaté dans le fichier de log principal.
    C'est le seul endroit où nous écrivons directement dans le fichier de log.

    Args:
        message (str): Le message à enregistrer.
    """
    log_file = config.get_log_file()
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception as e:
        # Si la journalisation échoue, on imprime sur la sortie d'erreur standard.
        # C'est notre filet de sécurité.
        print(f"FATAL: Impossible d'écrire dans le fichier de log {log_file}: {e}")
        print(f"FATAL: Message original: {message}")

# Ce module est destiné à être importé, pas exécuté directement.
