import re
import time
from typing import Dict, Any, List, Set

# --- Dépendances externes ---
try:
    import psutil
except ImportError:
    psutil = None

# --- Dépendances inter-modules ---
from ..db.database import SurveillanceDatabase
from ..core.config import CONFIG

class ProcessMonitor:
    """Surveille les processus système, en se concentrant sur les processus critiques et les patterns définis."""

    def __init__(self, db: SurveillanceDatabase):
        if not psutil:
            raise ImportError("Le module 'psutil' est requis pour ProcessMonitor.")
        self.db = db
        self.known_processes: Dict[int, Dict[str, Any]] = {}
        self.critical_processes: Set[str] = set(CONFIG.get("CRITICAL_PROCESSES", []))
        self.patterns = [re.compile(p, re.IGNORECASE) for p in CONFIG.get("PROCESS_PATTERNS", [])]

    def scan_processes(self):
        """
        Scan complet des processus. Identifie les nouveaux processus, les processus terminés,
        et surveille l'état des processus critiques.
        """
        current_pids = set()

        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'cpu_percent', 'memory_info', 'num_threads']):
            try:
                pid = proc.info['pid']
                current_pids.add(pid)

                # Si le processus est nouveau et correspond aux patterns, on le traite
                if pid not in self.known_processes and self._matches_patterns(proc.info):
                    self.handle_new_process(proc.info)

                # Surveillance spécifique pour les processus déjà connus
                elif pid in self.known_processes:
                    self.monitor_known_process(proc.info)

            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                continue

        # Détecter les processus qui se sont terminés depuis le dernier scan
        terminated_pids = set(self.known_processes.keys()) - current_pids
        for pid in terminated_pids:
            self.handle_terminated_process(pid)

    def _matches_patterns(self, proc_info: Dict[str, Any]) -> bool:
        """Vérifie si le nom du processus ou sa ligne de commande correspond aux patterns."""
        cmdline = ' '.join(proc_info.get('cmdline') or [])
        name = proc_info.get('name', '')
        text_to_check = f"{name} {cmdline}"
        return any(p.search(text_to_check) for p in self.patterns)

    def handle_new_process(self, proc_info: Dict[str, Any]):
        """Gère un nouveau processus détecté."""
        pid = proc_info['pid']
        self.known_processes[pid] = {
            'pid': pid,
            'name': proc_info.get('name'),
            'cmdline': ' '.join(proc_info.get('cmdline') or []),
            'status': proc_info.get('status'),
            'cpu_percent': proc_info.get('cpu_percent'),
            'memory_mb': (proc_info['memory_info'].rss / 1024 / 1024) if proc_info.get('memory_info') else 0,
            'threads': proc_info.get('num_threads')
        }
        self.db.log_process(self.known_processes[pid])

        if self._is_critical(self.known_processes[pid]):
            self.db.log_alert("critical_process_started", "INFO", f"Processus critique démarré: {proc_info['name']}", proc_info)

    def handle_terminated_process(self, pid: int):
        """Gère un processus qui s'est terminé."""
        terminated_info = self.known_processes.pop(pid)
        terminated_info['status'] = 'terminated'
        self.db.log_process(terminated_info)

        if self._is_critical(terminated_info):
            self.db.log_alert("critical_process_terminated", "HIGH", f"Processus critique terminé: {terminated_info['name']}", terminated_info)

    def monitor_known_process(self, proc_info: Dict[str, Any]):
        """Surveille les changements d'état ou de ressources pour un processus connu."""
        pid = proc_info['pid']

        # Mettre à jour les infos
        self.known_processes[pid]['status'] = proc_info['status']
        self.known_processes[pid]['cpu_percent'] = proc_info['cpu_percent']
        self.known_processes[pid]['memory_mb'] = (proc_info['memory_info'].rss / 1024 / 1024) if proc_info.get('memory_info') else 0

        # Loguer seulement si c'est un processus critique pour éviter le bruit
        if self._is_critical(self.known_processes[pid]):
            self.db.log_process(self.known_processes[pid])

            # Vérifier l'état
            if proc_info['status'] != psutil.STATUS_RUNNING:
                self.db.log_alert("critical_process_not_running", "WARNING", f"Processus critique {proc_info['name']} n'est pas en cours d'exécution (status: {proc_info['status']})", proc_info)

    def _is_critical(self, proc_info: Dict[str, Any]) -> bool:
        """Vérifie si un processus est critique."""
        text_to_check = f"{proc_info.get('name', '')} {proc_info.get('cmdline', '')}"
        return any(crit in text_to_check for crit in self.critical_processes)
