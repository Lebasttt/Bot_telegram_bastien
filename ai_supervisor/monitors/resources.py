import os
import time
import threading
from collections import deque
from typing import Dict, Any, List, Optional, Tuple

# --- Dépendances externes ---
try:
    import psutil
except ImportError:
    psutil = None

# --- Dépendances inter-modules ---
from ..db.database import SurveillanceDatabase
from ..core.config import CONFIG

class AdvancedResourceMonitor:
    """Surveille les ressources système, établit une baseline et détecte les anomalies."""

    def __init__(self, db: SurveillanceDatabase):
        if not psutil:
            raise ImportError("Le module 'psutil' est requis pour AdvancedResourceMonitor.")
        self.db = db
        self.history: deque = deque(maxlen=100) # Garder un historique plus court
        self.baseline: Optional[Dict[str, float]] = None
        self.monitoring = False
        self.thread = None

    def start_monitoring(self):
        """Démarre le thread de surveillance des ressources."""
        if self.monitoring:
            return
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("Surveillance des ressources active.")

    def stop_monitoring(self):
        """Arrête la surveillance."""
        self.monitoring = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _establish_baseline(self, duration_sec: int = 60):
        """Établit une baseline de performance sur une période donnée."""
        print(f"Établissement de la baseline de performance pour {duration_sec} secondes...")
        baseline_data: List[Dict[str, Any]] = []
        end_time = time.time() + duration_sec

        while time.time() < end_time:
            metrics = self._collect_metrics()
            if metrics:
                baseline_data.append(metrics)
            time.sleep(2) # Collecter des points de données toutes les 2 secondes

        if not baseline_data:
            print("Impossible d'établir la baseline, aucune donnée collectée.")
            return

        # Calculer les moyennes pour la baseline
        self.baseline = {
            'cpu_percent': sum(m['cpu_percent'] for m in baseline_data) / len(baseline_data),
            'memory_used_mb': sum(m['memory_used_mb'] for m in baseline_data) / len(baseline_data),
            'load_average_1m': sum(m['load_average_1m'] for m in baseline_data) / len(baseline_data),
        }
        print(f"Baseline établie: {self.baseline}")

    def _monitor_loop(self):
        """Boucle principale de surveillance des ressources."""
        # Établir une baseline au démarrage
        self._establish_baseline()

        interval = CONFIG.get("CHECK_INTERVALS", {}).get("resources", 5)
        while self.monitoring:
            metrics = self._collect_metrics()
            if not metrics:
                time.sleep(interval)
                continue

            self.history.append(metrics)
            self.db.log_performance(metrics)

            anomalies = self._detect_anomalies(metrics)
            if anomalies:
                self._handle_anomalies(anomalies, metrics)

            time.sleep(interval)

    def _collect_metrics(self) -> Optional[Dict[str, Any]]:
        """Collecte un instantané des métriques de performance système."""
        try:
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            return {
                'timestamp': time.time(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_used_mb': psutil.virtual_memory().used / (1024 * 1024),
                'memory_available_mb': psutil.virtual_memory().available / (1024 * 1024),
                'disk_usage_percent': psutil.disk_usage(CONFIG.get("SANDBOX_PATH", ".")).percent,
                'load_average_1m': load_avg[0],
                'load_average_5m': load_avg[1],
                'load_average_15m': load_avg[2]
            }
        except Exception as e:
            print(f"Erreur lors de la collecte des métriques: {e}")
            return None

    def _detect_anomalies(self, metrics: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Compare les métriques actuelles à la baseline pour détecter des déviations."""
        if not self.baseline:
            return []

        anomalies = []
        thresholds = CONFIG.get("RESOURCE_ANOMALY_THRESHOLDS", {})

        # CPU
        if self.baseline['cpu_percent'] > 1.0: # Éviter la division par zéro
            cpu_dev = abs(metrics['cpu_percent'] - self.baseline['cpu_percent']) / self.baseline['cpu_percent']
            if cpu_dev > thresholds.get('cpu_deviation', 0.5):
                anomalies.append(('cpu', cpu_dev))

        # Mémoire
        if self.baseline['memory_used_mb'] > 1.0:
            mem_dev = abs(metrics['memory_used_mb'] - self.baseline['memory_used_mb']) / self.baseline['memory_used_mb']
            if mem_dev > thresholds.get('memory_deviation', 0.3):
                anomalies.append(('memory', mem_dev))

        return anomalies

    def _handle_anomalies(self, anomalies: List[Tuple[str, float]], metrics: Dict[str, Any]):
        """Enregistre les anomalies détectées comme des alertes."""
        for resource, deviation in anomalies:
            message = f"Anomalie de ressource détectée pour '{resource}'. Déviation: {deviation:.2%}"
            details = {
                "resource": resource,
                "deviation": deviation,
                "current_metrics": metrics,
                "baseline": self.baseline
            }
            self.db.log_alert("resource_anomaly", "HIGH", message, details)
