import re
import time
import threading
from typing import Dict, Any, Set

# --- Dépendances externes ---
try:
    import psutil
except ImportError:
    psutil = None

# --- Dépendances inter-modules ---
from ..db.database import SurveillanceDatabase
from ..core.config import CONFIG

class NetworkMonitor:
    """Surveille les connexions réseau et détecte les activités suspectes."""

    def __init__(self, db: SurveillanceDatabase):
        if not psutil:
            raise ImportError("Le module 'psutil' est requis pour NetworkMonitor.")
        self.db = db
        self.known_connections: Set[str] = set()
        self.monitoring = False
        self.thread = None

    def start_monitoring(self):
        """Démarre le thread de surveillance du réseau."""
        if self.monitoring:
            return
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("Surveillance réseau active.")

    def stop_monitoring(self):
        """Arrête la surveillance."""
        self.monitoring = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _monitor_loop(self):
        """Boucle principale qui scanne périodiquement les connexions réseau."""
        interval = CONFIG.get("CHECK_INTERVALS", {}).get("network", 10)
        while self.monitoring:
            current_connections = set()
            try:
                for conn in psutil.net_connections(kind='inet'):
                    conn_id = self._get_connection_id(conn)
                    current_connections.add(conn_id)

                    if conn_id not in self.known_connections:
                        self._handle_new_connection(conn)

                self.known_connections = current_connections
            except Exception as e:
                print(f"Erreur lors du scan des connexions réseau: {e}")

            time.sleep(interval)

    def _get_connection_id(self, conn) -> str:
        """Crée un identifiant unique pour une connexion."""
        laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
        raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
        return f"{laddr}-{raddr}-{conn.pid or 'N/A'}"

    def _handle_new_connection(self, conn):
        """Gère une nouvelle connexion détectée."""
        try:
            proc_name = psutil.Process(conn.pid).name() if conn.pid else "unknown"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_name = "inaccessible"

        event_info = {
            'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
            'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
            'status': conn.status,
            'pid': conn.pid,
            'process_name': proc_name
        }

        self.db.log_network_event(event_info)

        if self._is_suspicious(event_info):
            self.db.log_alert(
                "suspicious_connection", "MEDIUM",
                f"Connexion suspecte détectée: {proc_name} -> {event_info['remote_address']}",
                event_info
            )

    def _is_suspicious(self, conn_info: Dict[str, Any]) -> bool:
        """Détermine si une connexion est suspecte."""
        if not conn_info['remote_address']:
            return False

        r_ip, r_port_str = conn_info['remote_address'].rsplit(':', 1)
        r_port = int(r_port_str)

        # Ports connus pour des activités malveillantes ou inhabituelles
        suspicious_ports = {6667, 31337, 12345, 4444}
        if r_port in suspicious_ports:
            return True

        # Connexions sortantes sur des ports non standards par des processus non-navigateurs
        common_web_ports = {80, 443}
        proc_name = (conn_info.get('process_name') or "").lower()
        is_browser = any(b in proc_name for b in ['firefox', 'chrome', 'safari', 'edge'])

        if r_port not in common_web_ports and not is_browser:
            return True

        return False
