import os
import shutil
import time
from typing import Optional

# --- Dépendances inter-modules ---
from ..core.config import CONFIG
from ..core.security import jules_safe, SecurityError, validate_sandbox_access

@jules_safe
def backup_configuration() -> Optional[str]:
    """
    Crée une sauvegarde horodatée du fichier de configuration principal.
    """
    # Le chemin de la configuration n'est pas dans la config elle-même,
    # nous devons le reconstruire ou le récupérer.
    supervisor_root = os.path.dirname(os.path.dirname(__file__)) # Remonte à ai_supervisor/
    config_path = os.path.join(supervisor_root, "config.json")

    if not os.path.exists(config_path):
        print(f"Le fichier de configuration {config_path} n'existe pas, impossible de le sauvegarder.")
        return None

    backup_dir = os.path.join(supervisor_root, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_file_path = os.path.join(backup_dir, f"config_{timestamp}.json.bak")

    try:
        # Valider que la destination est bien dans le sandbox
        validate_sandbox_access(backup_file_path)
        shutil.copyfile(config_path, backup_file_path)
        print(f"Configuration sauvegardée dans : {backup_file_path}")
        return backup_file_path
    except (IOError, SecurityError) as e:
        print(f"Erreur lors de la sauvegarde de la configuration: {e}")
        return None

@jules_safe
def cleanup_old_logs(max_age_days: int = 7) -> List[str]:
    """
    Nettoie les anciens fichiers de log et de snapshot.

    :param max_age_days: L'âge maximum en jours des fichiers à conserver.
    :return: La liste des fichiers supprimés.
    """
    deleted_files = []
    now = time.time()
    max_age_seconds = max_age_days * 86400

    # 1. Nettoyer les fichiers de log de rotation (.log.1, .log.2, etc.)
    log_file = CONFIG.get("LOG_FILE")
    if log_file:
        log_pattern = f"{log_file}.*"
        for file_path in glob.glob(log_pattern):
            try:
                if os.path.getmtime(file_path) < (now - max_age_seconds):
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    logger.info(f"Ancien fichier de log supprimé: {file_path}")
            except OSError as e:
                logger.warning(f"Impossible de supprimer l'ancien fichier de log {file_path}: {e}")

    # 2. Nettoyer les anciens snapshots
    snapshot_dir = os.path.join(CONFIG.get("SANDBOX_PATH", "."), "snapshots")
    if os.path.isdir(snapshot_dir):
        snapshot_pattern = os.path.join(snapshot_dir, "snapshot_*.json")
        for file_path in glob.glob(snapshot_pattern):
            try:
                if os.path.getmtime(file_path) < (now - max_age_seconds):
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    logger.info(f"Ancien snapshot supprimé: {file_path}")
            except OSError as e:
                logger.warning(f"Impossible de supprimer l'ancien snapshot {file_path}: {e}")

    return deleted_files
