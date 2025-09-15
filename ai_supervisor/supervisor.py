import os
import time
import threading
from typing import Dict, Any, List

# --- Dépendances inter-modules ---
from .db.database import SurveillanceDatabase
from .monitors.process import ProcessMonitor
from .monitors.filesystem import FileSystemMonitor
from .monitors.logs import LogMonitor
from .monitors.resources import AdvancedResourceMonitor
from .monitors.network import NetworkMonitor
from .monitors.snapshot import SystemSnapshot
from .core.config import CONFIG

class UltimateSurveillanceSystem:
    """
    Système de surveillance intégral qui orchestre tous les moniteurs.
    """

    def __init__(self, db_process: SurveillanceDatabase, db_network: SurveillanceDatabase,
                 db_file: SurveillanceDatabase, db_performance: SurveillanceDatabase):
        self.process_monitor = ProcessMonitor(db_process)
        self.file_monitor = FileSystemMonitor(db_file)
        self.log_monitor = LogMonitor(db_file) # Les alertes de log vont dans la db fichier
        self.resource_monitor = AdvancedResourceMonitor(db_performance)
        self.network_monitor = NetworkMonitor(db_network)
        self.snapshot_taker = SystemSnapshot()

        self.monitoring = False
        self.threads: List[threading.Thread] = []

    def start_full_surveillance(self):
        """Démarre tous les threads de surveillance en arrière-plan."""
        if self.monitoring:
            print("La surveillance est déjà active.")
            return

        self.monitoring = True
        print("🚀 Démarrage de la surveillance intégrale...")

        # Démarrer les moniteurs qui gèrent leurs propres threads
        self.file_monitor.start_monitoring()
        self.log_monitor.start_monitoring()
        self.resource_monitor.start_monitoring()
        self.network_monitor.start_monitoring()

        # Démarrer les moniteurs basés sur une boucle (processus, snapshots)
        self.threads.append(threading.Thread(target=self._process_monitor_loop, daemon=True))
        self.threads.append(threading.Thread(target=self._snapshot_loop, daemon=True))

        for thread in self.threads:
            thread.start()

        print(f"✅ Surveillance intégrale active avec {len(self.threads) + 4} moniteurs.")

    def stop_surveillance(self):
        """Arrête tous les moniteurs."""
        if not self.monitoring:
            return

        print("🛑 Arrêt du système de surveillance...")
        self.monitoring = False

        # Arrêter les moniteurs qui gèrent leurs propres threads
        self.file_monitor.stop_monitoring()
        self.log_monitor.stop_monitoring()
        self.resource_monitor.stop_monitoring()
        self.network_monitor.stop_monitoring()

        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2)

        print("👋 Surveillance arrêtée.")
        # Prendre un dernier snapshot d'urgence
        self.trigger_emergency_snapshot()

    def _process_monitor_loop(self):
        interval = CONFIG.get("CHECK_INTERVALS", {}).get("processes", 5)
        while self.monitoring:
            self.process_monitor.scan_processes()
            time.sleep(interval)

    def _snapshot_loop(self):
        interval = CONFIG.get("CHECK_INTERVALS", {}).get("snapshots", 300)
        while self.monitoring:
            self.snapshot_taker.take_full_snapshot()
            time.sleep(interval)

    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état actuel de la surveillance."""
        return {
            "is_monitoring": self.monitoring,
            "process_monitor_known_processes": len(self.process_monitor.known_processes),
            "filesystem_monitor_known_files": len(self.file_monitor.file_hashes),
            "resource_monitor_baseline_set": self.resource_monitor.baseline is not None,
            "timestamp": time.time()
        }

    def trigger_emergency_snapshot(self):
        """Déclenche manuellement un snapshot complet du système."""
        print("Déclenchement d'un snapshot d'urgence...")
        return self.snapshot_taker.take_full_snapshot()
