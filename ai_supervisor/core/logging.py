import logging
import json
import os
import time
import threading
import uuid
from collections import deque
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

# Importer la configuration chargée
from .config import CONFIG

# Initialiser la file d'attente pour les logs
LOG_QUEUE = deque()
LOG_THREAD_RUNNING = False

def setup_logging_with_rotation() -> logging.Logger:
    """
    Configure le logging avec rotation automatique en utilisant les paramètres du fichier de configuration.
    """
    log_config = CONFIG.get("LOGGING", {})
    log_file_path = CONFIG.get("LOG_FILE", "ai_debug_log.ndjson")

    # Récupérer les paramètres avec des valeurs par défaut robustes
    log_level = log_config.get("LOG_LEVEL", "INFO").upper()
    max_bytes = int(log_config.get("MAX_LOG_SIZE_MB", 10)) * 1024 * 1024
    backup_count = int(log_config.get("BACKUP_COUNT", 5))

    # S'assurer que le répertoire du fichier de log existe
    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8',
        delay=True
    )

    handler.setFormatter(logging.Formatter(
        '%(asctime)s - JULES_DEBUG - %(levelname)s - %(message)s'
    ))

    logger = logging.getLogger("jules_debug")
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)

    # Mapper le niveau de log string à la constante logging
    numeric_level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(numeric_level)

    return logger

def _log_writer():
    """
    Thread qui écrit les entrées de la LOG_QUEUE dans le fichier de log.
    """
    global LOG_THREAD_RUNNING
    LOG_THREAD_RUNNING = True

    log_file_path = CONFIG.get("LOG_FILE", "ai_debug_log.ndjson")

    while LOG_THREAD_RUNNING or LOG_QUEUE:
        if LOG_QUEUE:
            entry = LOG_QUEUE.popleft()
            try:
                # Utiliser le logger standard pour écrire, pour bénéficier de la rotation
                # Alternativement, écrire directement si le format ndjson est strict
                with open(log_file_path, "a", encoding="utf-8", errors="replace") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                # En cas d'erreur, on log dans le logger standard
                logger.error(f"Erreur d'écriture du log asynchrone: {e}")
        else:
            time.sleep(0.1)

def emit(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Émet un événement structuré qui sera écrit de manière asynchrone dans le fichier de log.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "version": "jules_adapted_v2",
        "event": event_type,
        "time": time.time(),
        "payload": payload,
    }

    LOG_QUEUE.append(entry)
    return entry

# Initialiser le logger et démarrer le thread d'écriture
# Cela sera fait dans le main.py pour un contrôle plus fin
logger = setup_logging_with_rotation()
log_thread = None

def start_log_writer_thread():
    global log_thread
    if not log_thread or not log_thread.is_alive():
        log_thread = threading.Thread(target=_log_writer, daemon=True)
        log_thread.start()

def stop_log_writer_thread():
    global LOG_THREAD_RUNNING
    LOG_THREAD_RUNNING = False
    if log_thread and log_thread.is_alive():
        log_thread.join(timeout=2)

# Pour les imports directs, on peut exposer le logger
# logger = setup_logging_with_rotation()
# start_log_writer_thread()
