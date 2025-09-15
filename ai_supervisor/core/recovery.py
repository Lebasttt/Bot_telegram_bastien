import os
import sys
import time
import gc
import functools
import signal
import threading
import shutil
from typing import Dict, Any

# --- Dépendances externes (nécessitent une installation) ---
try:
    import psutil
except ImportError:
    psutil = None

# --- Dépendances inter-modules ---
from .config import CONFIG
from .logging import emit, logger
from .memory import log_to_memory, save_knowledge_to_memory
from .security import jules_safe

# --- Variables globales du module ---
EMERGENCY_MODE = False
SHUTDOWN_REQUESTED = False # Doit être géré de manière centralisée

# --- Fonctions de récupération de bas niveau ---

@jules_safe
def _reset_standard_streams() -> bool:
    """Réinitialise stdin, stdout, et stderr à leurs valeurs par défaut."""
    try:
        sys.stdin = sys.__stdin__
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        # Tenter de vider les flux
        for stream in [sys.stdout, sys.stderr]:
            if hasattr(stream, 'flush'):
                stream.flush()
        return True
    except Exception as e:
        logger.error(f"Échec de la réinitialisation des flux standards: {e}")
        return False

@jules_safe
def _force_garbage_collection() -> str:
    """Force un garbage collection complet sur 3 générations."""
    try:
        count_before = gc.get_count()
        for i in range(3):
            gc.collect(generation=2)
            time.sleep(0.01)
        count_after = gc.get_count()
        return f"GC forcé. Objets avant: {count_before}, après: {count_after}"
    except Exception as e:
        logger.error(f"Échec du garbage collection forcé: {e}")
        return f"Erreur GC: {e}"

@jules_safe
def _clear_all_caches() -> str:
    """Tente de vider tous les caches connus (importlib, functools, etc.)."""
    cleared_caches = []
    try:
        import importlib
        importlib.invalidate_caches()
        cleared_caches.append("importlib")
    except Exception: pass

    # Vider les caches lru_cache globaux
    # Note : c'est une heuristique, ne videra que les caches sur les fonctions décorées
    # directement dans les modules chargés.
    try:
        # Itérer sur une copie pour éviter les problèmes de modification pendant l'itération
        for module in list(sys.modules.values()):
            if module:
                for obj in list(vars(module).values()):
                    if hasattr(obj, 'cache_clear'):
                        try:
                            obj.cache_clear()
                        except Exception: pass
        cleared_caches.append("lru_cache")
    except Exception: pass

    return f"Caches vidés: {', '.join(cleared_caches)}"

@jules_safe
def _release_file_locks() -> str:
    """Tente de libérer les verrous de fichiers ouverts par le processus courant."""
    if not psutil: return "psutil non disponible."

    released_count = 0
    try:
        process = psutil.Process(os.getpid())
        open_files = process.open_files()
        for file_handle in open_files:
            try:
                # Ne fermer que les fichiers dans le sandbox pour la sécurité
                if file_handle.path.startswith(CONFIG["SANDBOX_PATH"]):
                    os.close(file_handle.fd)
                    released_count += 1
            except Exception:
                continue
        return f"{released_count} verrous de fichiers libérés."
    except Exception as e:
        logger.error(f"Échec de la libération des verrous de fichiers: {e}")
        return f"Erreur: {e}"

@jules_safe
def _kill_zombie_processes() -> str:
    """Termine les processus zombies enfants du processus courant."""
    if not psutil: return "psutil non disponible."

    killed_count = 0
    try:
        parent = psutil.Process(os.getpid())
        children = parent.children(recursive=True)
        for process in children:
            if process.status() == psutil.STATUS_ZOMBIE:
                process.wait() # Récupérer le statut du zombie
                killed_count += 1
        return f"{killed_count} processus zombies nettoyés."
    except Exception as e:
        logger.error(f"Échec du nettoyage des processus zombies: {e}")
        return f"Erreur: {e}"

# ... (les autres fonctions _ prefixed et les fonctions de nettoyage de modèle)

@jules_safe
def emergency_recovery() -> Dict[str, Any]:
    """Exécute une séquence d'actions de récupération d'urgence."""
    global EMERGENCY_MODE
    if EMERGENCY_MODE:
        return {"status": "Récupération d'urgence déjà en cours."}

    EMERGENCY_MODE = True
    log_to_memory("Début de la récupération d'urgence", "critical_error", 1.0)

    recovery_actions = {
        "reset_streams": _reset_standard_streams,
        "force_gc": _force_garbage_collection,
        "clear_caches": _clear_all_caches,
        "release_locks": _release_file_locks,
        "kill_zombies": _kill_zombie_processes,
        # Ajoutez ici les autres fonctions de récupération...
    }

    results = {}
    for name, action in recovery_actions.items():
        try:
            results[name] = action()
        except Exception as e:
            results[name] = f"Erreur: {e}"

    log_to_memory("Récupération d'urgence terminée", "critical_error", 0.9, {"results": results})
    EMERGENCY_MODE = False
    return results

# --- Système de récupération automatique ---

class AutoRecoverySystem:
    """Système qui surveille la santé et déclenche des récupérations."""
    def __init__(self):
        self.error_count = 0
        self.recovery_count = 0
        self.monitor_thread = None
        self.monitoring = False

    def start_monitoring(self, interval: int = 300):
        if self.monitoring: return
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self.monitor_thread.start()
        log_to_memory("Système de récupération automatique démarré", "system_health", 0.7, {"interval": interval})

    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        log_to_memory("Système de récupération automatique arrêté", "system_health", 0.7)

    def _monitor_loop(self, interval: int):
        while self.monitoring and not SHUTDOWN_REQUESTED:
            try:
                health = self._check_system_health()
                if not health["healthy"]:
                    self.error_count += 1
                    emit("system_health_poor", health)
                    if self.error_count >= 3:
                        logger.warning(f"Santé système critique détectée. Déclenchement de la récupération automatique (compteur: {self.recovery_count + 1}).")
                        self._trigger_auto_recovery(health)
                        self.error_count = 0 # Réinitialiser après récupération
                else:
                    self.error_count = max(0, self.error_count - 1)

                time.sleep(interval)
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance de récupération: {e}")
                time.sleep(interval) # Attendre avant de réessayer

    def _check_system_health(self) -> Dict[str, Any]:
        """Vérifie les métriques système critiques."""
        if not psutil: return {"healthy": True, "reason": "psutil non disponible"}

        health = {"healthy": True, "timestamp": time.time(), "metrics": {}}
        process = psutil.Process(os.getpid())

        # Mémoire
        mem_percent = process.memory_percent()
        health["metrics"]["process_memory_percent"] = mem_percent
        if mem_percent > CONFIG["MEMORY_THRESHOLD"]:
            health["healthy"] = False

        # CPU
        cpu_percent = process.cpu_percent(interval=1)
        health["metrics"]["process_cpu_percent"] = cpu_percent
        if cpu_percent > CONFIG["CPU_THRESHOLD"]:
            health["healthy"] = False

        # Disque
        disk_usage = psutil.disk_usage(CONFIG["SANDBOX_PATH"]).percent
        health["metrics"]["disk_usage_percent"] = disk_usage
        if disk_usage > CONFIG["DISK_USAGE_THRESHOLD"]:
            health["healthy"] = False

        return health

    def _trigger_auto_recovery(self, health_info: Dict):
        self.recovery_count += 1
        log_to_memory("Récupération automatique déclenchée", "auto_recovery", 0.9, {"count": self.recovery_count, "health_info": health_info})

        # Logique de récupération ciblée
        metrics = health_info.get("metrics", {})
        if metrics.get("process_memory_percent", 0) > CONFIG["MEMORY_THRESHOLD"]:
            logger.info("Problème de mémoire détecté. Actions: GC forcé, nettoyage caches.")
            _force_garbage_collection()
            _clear_all_caches()
        else:
            logger.info("Déclenchement de la récupération d'urgence générale.")
            emergency_recovery()

        save_knowledge_to_memory(
            f"Rapport de Récupération Automatique #{self.recovery_count}",
            f"Santé système: {health_info}",
            ["auto_recovery", "system_health"]
        )
