import os
import re
import time
import threading
import glob
from typing import Dict, List

# --- Dépendances inter-modules ---
from ..db.database import SurveillanceDatabase
from ..core.config import CONFIG

class LogMonitor:
    """Surveille en temps réel des fichiers de log pour y déceler des patterns d'erreur ou d'alerte."""

    def __init__(self, db: SurveillanceDatabase):
        self.db = db
        self.log_files_patterns: List[str] = CONFIG.get("LOG_FILES_TO_MONITOR", [])
        self.file_positions: Dict[str, int] = {}
        self.monitoring = False
        self.threads: List[threading.Thread] = []

        # Patterns pour la détection d'erreurs
        self.error_patterns = [
            re.compile(p, re.IGNORECASE) for p in
            ['ERROR', 'CRITICAL', 'FATAL', 'Exception', 'Traceback', 'failed', 'denied', 'unauthorized']
        ]

    def _discover_log_files(self) -> List[str]:
        """Découvre les fichiers de log concrets à partir des patterns de la configuration."""
        discovered_files = set()
        for pattern in self.log_files_patterns:
            # Utiliser glob pour gérer les wildcards
            try:
                matching_files = glob.glob(pattern, recursive=True)
                for file in matching_files:
                    if os.path.isfile(file):
                        discovered_files.add(file)
            except Exception as e:
                print(f"Erreur lors de la recherche du pattern de log '{pattern}': {e}")
        return list(discovered_files)

    def start_monitoring(self):
        """Démarre un thread de surveillance pour chaque fichier de log découvert."""
        if self.monitoring:
            return
        self.monitoring = True

        log_files = self._discover_log_files()
        print(f"Démarrage de la surveillance pour {len(log_files)} fichier(s) de log.")

        for log_file in log_files:
            thread = threading.Thread(target=self._tail_log, args=(log_file,), daemon=True)
            self.threads.append(thread)
            thread.start()

    def stop_monitoring(self):
        """Arrête tous les threads de surveillance."""
        self.monitoring = False
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1)

    def _tail_log(self, log_file: str):
        """Lit en continu les nouvelles lignes d'un fichier de log (similaire à `tail -f`)."""
        try:
            # Se positionner à la fin du fichier au démarrage
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, os.SEEK_END)
                self.file_positions[log_file] = f.tell()
        except FileNotFoundError:
            # Le fichier peut apparaître plus tard
            self.file_positions[log_file] = 0
        except Exception as e:
            print(f"Impossible d'ouvrir initialement {log_file}: {e}")
            return

        while self.monitoring:
            try:
                if not os.path.exists(log_file):
                    time.sleep(5) # Attendre que le fichier soit créé
                    continue

                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(self.file_positions.get(log_file, 0))

                    new_lines = f.readlines()
                    if new_lines:
                        for line in new_lines:
                            self._process_log_line(log_file, line.strip())
                        self.file_positions[log_file] = f.tell()

                time.sleep(2) # Intervalle de vérification
            except Exception as e:
                print(f"Erreur lors de la lecture de {log_file}: {e}")
                time.sleep(10) # Attendre plus longtemps en cas d'erreur persistante

    def _process_log_line(self, log_file: str, line: str):
        """Analyse une ligne de log pour y trouver des patterns d'erreur."""
        for pattern in self.error_patterns:
            if pattern.search(line):
                alert_details = {
                    'log_file': log_file,
                    'log_line': line,
                }
                self.db.log_alert(
                    alert_type="log_error_detected",
                    severity="WARNING",
                    message=f"Erreur potentielle détectée dans {os.path.basename(log_file)}",
                    details=alert_details
                )
                # On s'arrête au premier match pour ne pas créer d'alertes multiples pour la même ligne
                break
