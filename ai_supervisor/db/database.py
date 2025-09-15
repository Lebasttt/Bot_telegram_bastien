import sqlite3
import json
import time
from typing import Dict, Any, Optional

class SurveillanceDatabase:
    """
    Gère une base de données SQLite pour stocker l'historique de surveillance
    (processus, réseau, fichiers, performance, alertes).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _connect(self):
        """Établit une connexion à la base de données."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row

    def _close(self):
        """Ferme la connexion."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def execute(self, query: str, params: tuple = ()):
        """Exécute une requête avec gestion de la connexion."""
        try:
            self._connect()
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            self._conn.commit()
        finally:
            self._close()

    def init_database(self):
        """Crée les tables nécessaires si elles n'existent pas."""
        schema_queries = [
            '''CREATE TABLE IF NOT EXISTS processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, pid INTEGER, name TEXT,
                cmdline TEXT, status TEXT, cpu_percent REAL, memory_mb REAL, threads INTEGER
            )''',
            '''CREATE TABLE IF NOT EXISTS network_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, local_address TEXT,
                remote_address TEXT, status TEXT, pid INTEGER, process_name TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS file_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, event_type TEXT,
                file_path TEXT, process_pid INTEGER, process_name TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, cpu_percent REAL,
                memory_used_mb REAL, memory_available_mb REAL, disk_usage_percent REAL,
                load_average_1m REAL, load_average_5m REAL, load_average_15m REAL
            )''',
            '''CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, alert_type TEXT,
                severity TEXT, message TEXT, details TEXT
            )'''
        ]

        for query in schema_queries:
            self.execute(query)

    def log_process(self, process_info: Dict[str, Any]):
        query = '''INSERT INTO processes
                   (timestamp, pid, name, cmdline, status, cpu_percent, memory_mb, threads)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
        params = (
            time.time(), process_info.get('pid'), process_info.get('name'),
            process_info.get('cmdline'), process_info.get('status'),
            process_info.get('cpu_percent'), process_info.get('memory_mb'),
            process_info.get('threads')
        )
        self.execute(query, params)

    def log_network_event(self, event_info: Dict[str, Any]):
        query = '''INSERT INTO network_events
                   (timestamp, local_address, remote_address, status, pid, process_name)
                   VALUES (?, ?, ?, ?, ?, ?)'''
        params = (
            time.time(), event_info.get('local_address'), event_info.get('remote_address'),
            event_info.get('status'), event_info.get('pid'), event_info.get('process_name')
        )
        self.execute(query, params)

    def log_file_event(self, event_info: Dict[str, Any]):
        query = '''INSERT INTO file_events
                   (timestamp, event_type, file_path, process_pid, process_name)
                   VALUES (?, ?, ?, ?, ?)'''
        params = (
            time.time(), event_info.get('event_type'), event_info.get('file_path'),
            event_info.get('process_pid'), event_info.get('process_name')
        )
        self.execute(query, params)

    def log_performance(self, metrics: Dict[str, Any]):
        query = '''INSERT INTO performance
                   (timestamp, cpu_percent, memory_used_mb, memory_available_mb,
                    disk_usage_percent, load_average_1m, load_average_5m, load_average_15m)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
        params = (
            time.time(), metrics.get('cpu_percent'), metrics.get('memory_used_mb'),
            metrics.get('memory_available_mb'), metrics.get('disk_usage_percent'),
            metrics.get('load_average_1m'), metrics.get('load_average_5m'),
            metrics.get('load_average_15m')
        )
        self.execute(query, params)

    def log_alert(self, alert_type: str, severity: str, message: str, details: Optional[Dict] = None):
        query = '''INSERT INTO alerts (timestamp, alert_type, severity, message, details)
                   VALUES (?, ?, ?, ?, ?)'''
        params = (
            time.time(), alert_type, severity, message,
            json.dumps(details) if details else None
        )
        self.execute(query, params)
