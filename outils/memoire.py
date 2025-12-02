# -*- coding: utf-8 -*-
"""
Module de gestion de la mémoire à long terme de l'agent.
Contient la Mémoire Cognitive pour un apprentissage structuré.
"""

import json
import time
from pathlib import Path
from typing import Callable
from functools import wraps

# Importe uniquement les types et le config, pas les autres modules.
from . import config

class MemoireCognitive:
    """
    Cerveau structuré de l'agent. Reçoit ses dépendances (comme le logger)
    par injection pour rester un module indépendant.
    """
    def __init__(self, log_func: Callable[[str], None], filepath: Path = None):
        self.filepath = filepath or config.get_memoire_cognitive_file()
        self.log = log_func
        self.data = {
            "commandes": {},
            "capacites_auto": {},
            "stats_globales": {
                "total_executions": 0,
                "total_succes": 0,
                "total_echecs": 0,
                "dernier_nettoyage": time.time()
            }
        }
        self.charger()

    def charger(self):
        """Charge la mémoire depuis le fichier JSON."""
        try:
            if self.filepath.exists():
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                self.log(f"🧠 Mémoire cognitive chargée: {len(self.data.get('commandes', {}))} commandes suivies.")
        except (json.JSONDecodeError, IOError) as e:
            self.log(f"⚠️  Impossible de charger la mémoire cognitive ({e}), création d'une nouvelle mémoire.")
            self.sauvegarder()

    def sauvegarder(self):
        """Sauvegarde la mémoire dans le fichier JSON."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.log(f"❌ Erreur de sauvegarde de la mémoire cognitive: {e}")

    def enregistrer_execution_commande(self, commande: str, succes: bool):
        """Enregistre le résultat d'une commande standard."""
        if commande not in self.data["commandes"]:
            self.data["commandes"][commande] = {"succes": 0, "echecs": 0, "executions": 0}

        stats = self.data["commandes"][commande]
        stats["executions"] += 1
        self.data["stats_globales"]["total_executions"] += 1

        if succes:
            stats["succes"] += 1
            self.data["stats_globales"]["total_succes"] += 1
        else:
            stats["echecs"] += 1
            self.data["stats_globales"]["total_echecs"] += 1

        self.sauvegarder()

    def enregistrer_execution_capacite(self, nom_fonction: str, succes: bool):
        """Enregistre le résultat d'une capacité auto-générée."""
        if nom_fonction not in self.data["capacites_auto"]:
            self.data["capacites_auto"][nom_fonction] = {
                "succes": 0,
                "echecs": 0,
                "executions": 0,
                "creee_le": time.time(),
                "purgee": False
            }

        stats = self.data["capacites_auto"][nom_fonction]
        stats["executions"] += 1

        if succes:
            stats["succes"] += 1
        else:
            stats["echecs"] += 1

        self.log(f"📈 Suivi performance '{nom_fonction}': {stats['succes']} succès / {stats['executions']} exécutions.")
        self.sauvegarder()

# --- Décorateur pour le suivi de performance ---
# Note : Ce décorateur dépendra d'une instance globale de MemoireCognitive
# qui sera initialisée dans gpt2.py. C'est un compromis pour garder
# la syntaxe @suivi_performance_capacite simple.

_memoire_cognitive_instance = None

def set_global_memoire_instance(instance: MemoireCognitive):
    """Permet à gpt2.py de définir l'instance de mémoire à utiliser."""
    global _memoire_cognitive_instance
    _memoire_cognitive_instance = instance

def suivi_performance_capacite(func):
    """Décorateur pour tracer le succès/échec des fonctions auto-générées."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        nom_fonction = func.__name__
        succes = False
        # On suppose que la fonction est un échec si elle retourne une chaîne contenant 'ER_REUR' ou lève une exception.
        # Cette logique peut être affinée.
        is_echec_str = lambda s: isinstance(s, str) and "erreur" in s.lower()

        try:
            resultat = func(*args, **kwargs)
            if not is_echec_str(resultat):
                succes = True
            return resultat
        except Exception as e:
            # Pourrait appeler log() ici si on le passait en argument, mais
            # on garde simple pour l'instant.
            print(f"❌ La capacité '{nom_fonction}' a échoué avec une exception: {e}")
            succes = False
            return f"[❌ ERREUR CAPACITÉ] {e}"
        finally:
            if _memoire_cognitive_instance:
                _memoire_cognitive_instance.enregistrer_execution_capacite(nom_fonction, succes)
            else:
                # Log d'alerte si l'instance n'est pas définie
                print(f"⚠️ ALERTE: Instance de mémoire non définie. Impossible de suivre la performance de '{nom_fonction}'.")
    return wrapper
