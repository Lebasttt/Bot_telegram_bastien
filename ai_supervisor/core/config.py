import os
import json
from typing import Dict, Any

# Définir le chemin du sandbox de manière centralisée
SANDBOX_PATH = os.getenv("WORKSPACE", ".")
os.makedirs(SANDBOX_PATH, exist_ok=True)

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Charge la configuration depuis un fichier JSON.
    Le chemin est relatif au dossier 'ai_supervisor'.
    """
    # Construire le chemin absolu vers le fichier de config
    supervisor_dir = os.path.dirname(__file__)
    # Remonter de deux niveaux pour être à la racine du projet (/app)
    supervisor_root = os.path.dirname(os.path.dirname(supervisor_dir))
    absolute_config_path = os.path.join(supervisor_root, config_path)

    if not os.path.exists(absolute_config_path):
        raise FileNotFoundError(f"Le fichier de configuration {absolute_config_path} est introuvable.")

    with open(absolute_config_path, 'r') as f:
        config_data = json.load(f)

    return resolve_paths(config_data)

def resolve_paths(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Résout les chemins relatifs dans la configuration en les joignant au SANDBOX_PATH.
    """
    # Clés de configuration qui contiennent des chemins de fichiers/dossiers relatifs
    path_keys = [
        "LOG_FILE", "CRASH_FILE", "PID_FILE", "SECRETS_SCAN_FILE",
        "DEPENDENCY_AUDIT_FILE", "MEMORY_INTEGRATION_FILE",
        "PROCESS_DB", "NETWORK_DB", "FILE_DB", "PERFORMANCE_DB"
    ]

    for key in path_keys:
        if key in config and isinstance(config[key], str):
            # Ne pas modifier les chemins qui sont déjà absolus
            if not os.path.isabs(config[key]):
                config[key] = os.path.join(SANDBOX_PATH, config[key])

    # Gérer les répertoires à surveiller
    if "WATCH_DIRECTORIES" in config:
        resolved_watch_dirs = []
        for directory in config["WATCH_DIRECTORIES"]:
            if directory == ".":
                resolved_watch_dirs.append(SANDBOX_PATH)
            else:
                resolved_watch_dirs.append(directory)
        config["WATCH_DIRECTORIES"] = resolved_watch_dirs

    # Gérer les fichiers de log à surveiller (avec wildcards)
    if "LOG_FILES_TO_MONITOR" in config:
        resolved_log_files = []
        for pattern in config["LOG_FILES_TO_MONITOR"]:
            # Si le pattern ne contient pas de séparateur de chemin, on le considère relatif
            if not os.path.sep in pattern:
                 resolved_log_files.append(os.path.join(SANDBOX_PATH, pattern))
            else:
                 resolved_log_files.append(pattern)
        config["LOG_FILES_TO_MONITOR"] = resolved_log_files

    # Ajouter le SANDBOX_PATH à la config pour un accès facile
    config["SANDBOX_PATH"] = SANDBOX_PATH

    return config

# Charger la configuration au démarrage du module
try:
    CONFIG = load_config()
except Exception as e:
    print(f"ERREUR CRITIQUE: Impossible de charger la configuration. {e}")
    # Utiliser une config vide pour éviter de planter d'autres imports
    CONFIG = {"error": str(e)}
