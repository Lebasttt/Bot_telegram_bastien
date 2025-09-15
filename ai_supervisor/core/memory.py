import os
import json
import time
from typing import Any, Dict, List, Optional

from .config import CONFIG
from .logging import emit, logger
from .security import jules_safe

# Récupérer les chemins depuis la config
MEMORY_INTEGRATION_FILE = CONFIG.get("MEMORY_INTEGRATION_FILE")
KNOWLEDGE_BASE_FILE = os.path.join(CONFIG.get("SANDBOX_PATH", "."), "knowledge_base.json")
CURRENT_TASK_ID = str(time.time()) # Placeholder, pourrait être géré de manière plus dynamique

@jules_safe
def log_to_memory(activity: str, category: str = "debug", importance: float = 0.5,
                  metadata: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    """
    Enregistre une activité dans le fichier d'intégration mémoire.
    """
    if not MEMORY_INTEGRATION_FILE:
        logger.warning("MEMORY_INTEGRATION_FILE n'est pas défini dans la configuration.")
        return None

    if metadata is None:
        metadata = {}

    log_entry = {
        "timestamp": time.time(),
        "activity": activity,
        "category": category,
        "importance": importance,
        "task_id": CURRENT_TASK_ID,
        "metadata": metadata
    }

    try:
        memory_data = []
        if os.path.exists(MEMORY_INTEGRATION_FILE):
            try:
                with open(MEMORY_INTEGRATION_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        memory_data = json.loads(content)
            except (json.JSONDecodeError, IOError):
                logger.warning(f"Impossible de lire ou parser {MEMORY_INTEGRATION_FILE}. Le fichier sera écrasé.")
                memory_data = []

        if not isinstance(memory_data, list):
            logger.warning(f"Le contenu de {MEMORY_INTEGRATION_FILE} n'est pas une liste. Le fichier sera écrasé.")
            memory_data = []

        memory_data.append(log_entry)

        with open(MEMORY_INTEGRATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=2)

    except Exception as e:
        logger.error(f"Erreur d'écriture dans le fichier mémoire {MEMORY_INTEGRATION_FILE}: {e}")
        return None

    # Émettre également un événement de débogage pour le suivi en temps réel
    emit("memory_log", {
        "activity": activity,
        "category": category,
        "importance": importance,
        "metadata": metadata
    })

    return log_entry

@jules_safe
def save_knowledge_to_memory(title: str, content: str, tags: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Sauvegarde une connaissance structurée dans la base de connaissances.
    """
    if tags is None:
        tags = ["debug", "knowledge"]

    knowledge_entry = {
        "id": str(time.time()), # Simple ID basé sur le timestamp
        "timestamp": time.time(),
        "title": title,
        "content": content,
        "tags": tags,
        "task_id": CURRENT_TASK_ID
    }

    try:
        knowledge_data = []
        if os.path.exists(KNOWLEDGE_BASE_FILE):
            try:
                with open(KNOWLEDGE_BASE_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        knowledge_data = json.loads(content)
            except (json.JSONDecodeError, IOError):
                logger.warning(f"Impossible de lire ou parser {KNOWLEDGE_BASE_FILE}. Le fichier sera écrasé.")
                knowledge_data = []

        if not isinstance(knowledge_data, list):
            logger.warning(f"Le contenu de {KNOWLEDGE_BASE_FILE} n'est pas une liste. Le fichier sera écrasé.")
            knowledge_data = []

        knowledge_data.append(knowledge_entry)

        with open(KNOWLEDGE_BASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(knowledge_data, f, indent=2)

    except Exception as e:
        logger.error(f"Erreur de sauvegarde de connaissance dans {KNOWLEDGE_BASE_FILE}: {e}")
        return None

    log_to_memory(f"Connaissance sauvegardée: {title}", "knowledge", 0.7, {"tags": tags, "title": title})

    return knowledge_entry

@jules_safe
def get_recent_memory_activities(limit: int = 10) -> List[Dict]:
    """
    Récupère les activités récentes depuis le fichier d'intégration mémoire.
    """
    if not MEMORY_INTEGRATION_FILE or not os.path.exists(MEMORY_INTEGRATION_FILE):
        return []

    try:
        with open(MEMORY_INTEGRATION_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return []
            memory_data = json.loads(content)
            if isinstance(memory_data, list):
                return memory_data[-limit:]
            else:
                return []
    except (json.JSONDecodeError, IOError, TypeError) as e:
        logger.error(f"Impossible de récupérer les activités mémoire: {e}")
        return []
