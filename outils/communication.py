# -*- coding: utf-8 -*-
"""
Module gérant la communication sortante de l'agent, comme les mises à jour
de statut et l'archivage des actions.
"""

from datetime import datetime
from typing import Callable

from . import config

def update_comm(message: str, log_func: Callable[[str], None]):
    """
    Écrit un message dans le fichier de communication destiné à l'utilisateur
    et le journalise également.
    """
    try:
        with open(config.get_comm_file(), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%F %T')}] - [Évolution]: {message}\n")
        log_func(f"📢 Communication: {message}")
    except Exception as e:
        log_func(f"❌ Erreur lors de la mise à jour de la communication: {e}")

def archive_automatique(origine: str, commande: str, resultat: str, log_func: Callable[[str], None]):
    """
    Archive une action complète (origine, commande, résultat) dans le fichier
    d'archives principal.
    """
    timestamp = datetime.now().strftime('%F %T')
    try:
        with open(config.get_archive_file(), "a", encoding="utf-8") as f:
            f.write(f"=== ARCHIVE [{timestamp}] ===\n")
            f.write(f"ORIGINE: {origine}\n")
            f.write(f"COMMANDE: {commande}\n")
            f.write(f"RESULTAT:\n{resultat}\n")
            f.write("=== FIN ARCHIVE ===\n\n")
        log_func(f"💾 Archivé automatiquement: {commande}")
    except Exception as e:
        log_func(f"❌ Erreur lors de l'archivage automatique: {e}")
