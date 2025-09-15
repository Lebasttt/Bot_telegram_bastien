import os
import re
import time
import threading
import hashlib
from typing import Dict, Any

# --- Dépendances inter-modules ---
from ..db.database import SurveillanceDatabase
from ..core.config import CONFIG

class FileSystemMonitor:
    """Surveille les changements dans le système de fichiers (création, modification, suppression)."""

    def __init__(self, db: SurveillanceDatabase):
        self.db = db
        self.watched_directories: list[str] = CONFIG.get("WATCH_DIRECTORIES", [])
        self.file_hashes: Dict[str, str] = {}
        self.monitoring = False
        self.thread = None

    def start_monitoring(self):
        """Démarre le thread de surveillance du système de fichiers."""
        if self.monitoring:
            return
        self.monitoring = True
        # Initialiser l'état des fichiers
        print("Initialisation de l'état du système de fichiers...")
        self._initialize_file_states()

        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("Surveillance du système de fichiers active.")

    def stop_monitoring(self):
        """Arrête la surveillance."""
        self.monitoring = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _initialize_file_states(self):
        """Scan initial pour peupler les hashes des fichiers existants."""
        for directory in self.watched_directories:
            if not os.path.isdir(directory):
                continue
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.file_hashes[file_path] = self._calculate_file_hash(file_path)

    def _monitor_loop(self):
        """Boucle principale qui scanne périodiquement les répertoires."""
        interval = CONFIG.get("CHECK_INTERVALS", {}).get("filesystem", 30)
        while self.monitoring:
            current_files = set()
            for directory in self.watched_directories:
                if not os.path.isdir(directory):
                    continue
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        current_files.add(file_path)

                        if file_path not in self.file_hashes:
                            self._handle_new_file(file_path)
                        else:
                            self._check_file_modification(file_path)

            deleted_files = set(self.file_hashes.keys()) - current_files
            for file_path in deleted_files:
                self._handle_deleted_file(file_path)

            time.sleep(interval)

    def _handle_new_file(self, file_path: str):
        """Gère la détection d'un nouveau fichier."""
        event_info = {'event_type': 'created', 'file_path': file_path}
        self.db.log_file_event(event_info)
        self.file_hashes[file_path] = self._calculate_file_hash(file_path)
        if self._is_suspicious(file_path):
            self.db.log_alert("suspicious_file_created", "MEDIUM", f"Fichier suspect créé: {file_path}", event_info)

    def _handle_deleted_file(self, file_path: str):
        """Gère la suppression d'un fichier."""
        event_info = {'event_type': 'deleted', 'file_path': file_path}
        self.db.log_file_event(event_info)
        del self.file_hashes[file_path]
        if self._is_important(file_path):
            self.db.log_alert("important_file_deleted", "HIGH", f"Fichier important supprimé: {file_path}", event_info)

    def _check_file_modification(self, file_path: str):
        """Vérifie si un fichier a été modifié en comparant les hashes."""
        current_hash = self._calculate_file_hash(file_path)
        if current_hash != "unreadable" and self.file_hashes.get(file_path) != current_hash:
            event_info = {'event_type': 'modified', 'file_path': file_path}
            self.db.log_file_event(event_info)
            self.file_hashes[file_path] = current_hash
            if self._is_important(file_path):
                self.db.log_alert("important_file_modified", "WARNING", f"Fichier important modifié: {file_path}", event_info)

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calcule le hash SHA256 d'un fichier."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (IOError, OSError):
            return "unreadable"

    def _is_suspicious(self, file_path: str) -> bool:
        """Détermine si un nom de fichier est suspect (binaire, script temporaire)."""
        suspicious_exts = ['.exe', '.bat', '.sh', '.vbs', '.tmp', '.temp', '.swp']
        return any(file_path.lower().endswith(ext) for ext in suspicious_exts)

    def _is_important(self, file_path: str) -> bool:
        """Détermine si un fichier est potentiellement important (config, db, etc.)."""
        important_names = ['config', 'settings', 'secret', 'password', '.env', '.db', '.sqlite']
        return any(name in file_path.lower() for name in important_names)
