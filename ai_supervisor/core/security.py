import os
import functools
from typing import Callable

# Placeholder pour le logger
import logging
from .config import CONFIG

logger = logging.getLogger("jules_debug")

# SANDBOX_PATH sera initialisé à partir de la config
SANDBOX_PATH = CONFIG.get("SANDBOX_PATH", os.getenv("WORKSPACE", "."))

class SecurityError(Exception):
    """Exception pour les violations de sécurité du sandbox"""
    pass

def validate_sandbox_access(path: str) -> bool:
    """Valide que l'accès est limité au sandbox Jules"""
    if not path:
        return True

    # Chemins absolus potentiellement dangereux (liste non exhaustive)
    # Note : Cette logique est simplifiée, une approche par liste blanche serait plus sûre.
    forbidden_starts = ['/', '/home', '/etc', '/usr', '/bin', '/sbin', '/var', '/tmp']

    try:
        real_path = os.path.realpath(path)
    except OSError:
        # Le chemin n'existe pas, on le traite comme une chaîne
        real_path = os.path.abspath(path)

    if not real_path.startswith(SANDBOX_PATH):
        # Vérifier si c'est un chemin absolu interdit qui n'est pas dans le sandbox
        # (par exemple, si SANDBOX_PATH est /app/sandbox et le chemin est /etc/passwd)
        if any(real_path.startswith(forbidden) for forbidden in forbidden_starts):
            raise SecurityError(f"Accès interdit en dehors du sandbox: {path}")

    return True

def validate_file_extension(file_path: str) -> bool:
    """
    Valide l'extension d'un fichier contre une liste blanche dans la configuration.
    """
    allowed_exts = CONFIG.get("SECURITY", {}).get("ALLOWED_EXTENSIONS", [])
    if not allowed_exts:
        # Si aucune extension n'est définie, on autorise tout pour ne pas bloquer.
        return True

    extension = os.path.splitext(file_path)[1]
    if not extension or extension.lower() not in allowed_exts:
        raise SecurityError(f"Extension de fichier non autorisée: {extension}")

    return True

def jules_safe(func: Callable) -> Callable:
    """Décorateur de sécurité pour toutes les fonctions critiques"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Validation des arguments de type chemin
            all_args = list(args) + list(kwargs.values())
            for arg in all_args:
                if isinstance(arg, str) and ('/' in arg or '\\' in arg):
                    # On ne valide que les chemins qui semblent être des chemins de fichiers/dossiers
                    # Cela évite de valider des chaînes comme des URL ou des regex
                    if os.path.sep in arg and len(arg) < 1024:
                         validate_sandbox_access(arg)

            return func(*args, **kwargs)
        except SecurityError as e:
            logger.error(f"Violation de sécurité dans {func.__name__}: {e}")
            # Dans un système modulaire, on ne retourne pas de dict, on lève l'exception
            # ou on la gère de manière plus centralisée. Pour l'instant, on la lève.
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue dans la fonction sécurisée {func.__name__}: {e}")
            # Laisser l'exception remonter pour être gérée par le handler global.
            raise
    return wrapper
