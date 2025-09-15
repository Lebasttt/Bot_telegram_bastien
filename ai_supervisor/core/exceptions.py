import sys
import traceback
import os
import threading
import json
import time
import faulthandler
from typing import List, Dict, Any, Optional

# --- Dépendances inter-modules ---
# Celles-ci seront résolues une fois que tous les fichiers seront créés.
from .config import CONFIG
from .logging import emit, logger
from .memory import save_knowledge_to_memory, get_recent_memory_activities
from ..utils.helpers import compress_report

# --- Placeholders pour les dépendances futures ---
def emergency_recovery() -> Dict:
    logger.warning("Placeholder: emergency_recovery() a été appelé.")
    return {"status": "placeholder_recovery"}

def analyze_root_cause(error_info: Dict, recent_activities: Optional[List[Dict]] = None) -> Dict:
    logger.warning("Placeholder: analyze_root_cause() a été appelé.")
    return {"summary": "placeholder_analysis"}

def analyze_temporal_patterns() -> Dict:
    logger.warning("Placeholder: analyze_temporal_patterns() a été appelé.")
    return {"status": "placeholder_temporal_analysis"}

# --- Variables globales du module ---
CRASH_FILE = CONFIG.get("CRASH_FILE")
EMERGENCY_MODE = False # Cette variable globale doit être gérée de manière centralisée

def ultimate_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Hook d'exception ultime qui capture les erreurs non gérées, génère un rapport,
    et tente une récupération.
    """
    # Ne pas intercepter l'interruption manuelle
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical(f"Exception non gérée interceptée: {exc_type.__name__}: {exc_value}")

    try:
        # 1. Formatter la stack trace
        tb_list = traceback.extract_tb(exc_traceback)
        stack_trace = [
            {
                "filename": frame.filename,
                "line": frame.lineno,
                "function": frame.name,
                "code": frame.line
            } for frame in tb_list
        ]

        # 2. Créer le rapport d'exception
        exception_report = {
            "type": exc_type.__name__,
            "message": str(exc_value),
            "stack_trace": stack_trace,
            "timestamp": time.time(),
            "context": {
                "cwd": os.getcwd(),
                "pid": os.getpid(),
                "thread": threading.current_thread().name
            }
        }

        # 3. Sauvegarder le rapport de crash compressé
        if CRASH_FILE:
            try:
                compressed = compress_report(exception_report)
                with open(CRASH_FILE, "w", encoding="utf-8") as f:
                    f.write(compressed)
            except Exception as e:
                logger.error(f"Impossible de sauvegarder le rapport de crash: {e}")

        # 4. Émettre un événement pour le logging temps réel
        emit("unhandled_exception", exception_report)

        # 5. Sauvegarder dans la mémoire à long terme
        knowledge_content = f"Crash survenu: {exc_value}\n\nStack Trace:\n{json.dumps(stack_trace, indent=2)}"
        save_knowledge_to_memory(
            f"Rapport de Crash: {exc_type.__name__}",
            knowledge_content,
            ["crash", "error", exc_type.__name__]
        )

        # 6. Tenter une analyse de cause racine
        try:
            recent_activities = get_recent_memory_activities(10)
            root_cause = analyze_root_cause(exception_report, recent_activities)
            emit("root_cause_analysis_after_crash", root_cause)
        except Exception as e:
            logger.error(f"L'analyse de cause racine a échoué: {e}")

        # 7. Tenter une récupération d'urgence
        global EMERGENCY_MODE
        if not EMERGENCY_MODE:
            logger.info("Tentative de récupération d'urgence après exception...")
            recovery_results = emergency_recovery()
            emit("emergency_recovery_after_exception", recovery_results)

    except Exception as handler_error:
        # Si le gestionnaire lui-même échoue, on log en dernier recours
        logger.critical(f"ERREUR CRITIQUE DANS LE GESTIONNAIRE D'EXCEPTIONS: {handler_error}")
        try:
            with open("ultimate_handler_failure.log", "a") as f:
                f.write(f"{time.time()}: {handler_error}\n")
                f.write(f"Original exception: {exc_type.__name__}: {exc_value}\n")
        except:
            pass

    # Finalement, appeler le hook par défaut pour que l'erreur s'affiche dans la console
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def enable_ultimate_exception_hook():
    """Active la capture ultime des exceptions pour le thread principal."""
    sys.excepthook = ultimate_exception_handler
    faulthandler.enable()
    logger.info("Gestionnaire d'exceptions ultime et faulthandler activés.")
