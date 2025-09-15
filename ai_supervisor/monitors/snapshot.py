import os
import sys
import time
import json
from datetime import datetime
import re
from typing import Dict, Any, List

# --- Dépendances externes ---
try:
    import psutil
except ImportError:
    psutil = None

# --- Dépendances inter-modules ---
from ..core.config import CONFIG

class SystemSnapshot:
    """Prend et sauvegarde des snapshots complets de l'état du système."""

    def __init__(self):
        if not psutil:
            raise ImportError("Le module 'psutil' est requis pour SystemSnapshot.")
        self.snapshot_dir = os.path.join(CONFIG.get("SANDBOX_PATH", "."), "snapshots")
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def take_full_snapshot(self) -> Dict[str, Any]:
        """Prend un snapshot complet et le sauvegarde dans un fichier JSON."""
        snapshot = {
            'timestamp': time.time(),
            'system_info': self._get_system_info(),
            'performance': self._get_performance_snapshot(),
            'processes': self._get_process_snapshot(),
            'network': self._get_network_snapshot(),
            'filesystem': self._get_filesystem_snapshot(),
        }

        self._save_snapshot(snapshot)
        return snapshot

    def _save_snapshot(self, snapshot: Dict[str, Any]):
        """Sauvegarde le snapshot dans un fichier horodaté."""
        try:
            ts = datetime.fromtimestamp(snapshot['timestamp']).strftime("%Y%m%d_%H%M%S")
            snapshot_file = os.path.join(self.snapshot_dir, f"snapshot_{ts}.json")

            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2, default=str) # default=str pour les types non sérialisables
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du snapshot: {e}")

    def _get_system_info(self) -> Dict[str, Any]:
        """Collecte des informations générales sur le système."""
        return {
            'platform': sys.platform,
            'python_version': sys.version,
            'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown',
            'boot_time': psutil.boot_time(),
        }

    def _get_performance_snapshot(self) -> Dict[str, Any]:
        """Collecte les métriques de performance."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=None), # Non-blocking
                'memory': psutil.virtual_memory()._asdict(),
                'disk_io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                'net_io': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
            }
        except Exception:
            return {}

    def _get_process_snapshot(self) -> List[Dict[str, Any]]:
        """Collecte un instantané de tous les processus en cours."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def _get_network_snapshot(self) -> List[Dict[str, Any]]:
        """Collecte un instantané de toutes les connexions réseau."""
        connections = []
        try:
            for conn in psutil.net_connections(kind='all'):
                connections.append({
                    'fd': conn.fd,
                    'family': conn.family.name,
                    'type': conn.type.name,
                    'laddr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    'raddr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status,
                    'pid': conn.pid,
                })
        except Exception:
            pass
        return connections

    def _get_filesystem_snapshot(self) -> Dict[str, Any]:
        """Collecte des informations sur l'utilisation du disque."""
        return {
            'partitions': [p._asdict() for p in psutil.disk_partitions()],
            'usage': {
                p.mountpoint: psutil.disk_usage(p.mountpoint)._asdict()
                for p in psutil.disk_partitions() if os.path.exists(p.mountpoint)
            }
        }
