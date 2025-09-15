#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Système de Workflow Automatisé pour Jules - Version Raffinée et Fusionnée
Ce script fournit des outils complets pour automatiser les tâches d'ingénierie logicielle.
Il fonctionne en arrière-plan avec une interface CLI complète et un système de mémoire persistante.
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
import tempfile
import tarfile
import ast
import logging
import time
import signal
import threading
import hashlib
import re
import random
import inspect
import asyncio
import aiohttp
import psutil
import sqlparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from functools import wraps
from collections import defaultdict
import requests
import yaml
import platform
import graphviz
from packaging import version
from faker import Faker
import jinja2
from cryptography.fernet import Fernet
import base64
import memory_profiler
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field
import astor
from flask import Flask, render_template_string
import importlib.util

# numpy and sklearn are heavy dependencies, let's make them optional for now
# and add a check in the functions that use them.
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

# Déterminer le répertoire racine du projet pour construire des chemins absolus.
# This makes the script runnable from any directory.
SCRIPT_DIR = Path(__file__).resolve().parent

# Configuration des chemins
MEMORY_DIR = SCRIPT_DIR / ".jules_memory"
WORKSPACE_SNAPSHOTS_DIR = MEMORY_DIR / "workspace_snapshots"
MEMORY_FILE = MEMORY_DIR / "memory.json"
ACTIVITY_LOG = MEMORY_DIR / "activity.log"
REMINDERS_FILE = MEMORY_DIR / "reminders.md"
CONFIG_FILE = SCRIPT_DIR / "config.yaml"
PID_FILE = MEMORY_DIR / "daemon.pid"

# Configuration du démon
DAEMON_CHECK_INTERVAL = 60  # secondes
BACKGROUND_MODE = False
stop_event = None
daemon_thread = None


# =============================================================================
# CLASSES DE CONFIGURATION
# =============================================================================

class WorkflowConfig(BaseModel):
    memory_dir: str = Field(default=".jules_memory", description="Répertoire de mémoire")
    log_level: str = Field(default="INFO", description="Niveau de log")
    default_project_type: str = Field(default="python-api", description="Type de projet par défaut")
    max_snapshots: int = Field(default=10, description="Nombre maximum de snapshots")
    backup_enabled: bool = Field(default=True, description="Sauvegarde automatique activée")
    auto_cleanup_days: int = Field(default=30, description="Jours avant nettoyage des snapshots")


class ConfigManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            self.config_path = SCRIPT_DIR / "workflow_config.yaml"
        else:
            self.config_path = Path(config_path)
        self.config = self.load_config()

    def load_config(self) -> WorkflowConfig:
        if self.config_path.exists():
            try:
                if self.config_path.suffix == '.json':
                    with open(self.config_path, 'r') as f:
                        data = json.load(f)
                else:
                    with open(self.config_path, 'r') as f:
                        data = yaml.safe_load(f)
                return WorkflowConfig(**data)
            except (json.JSONDecodeError, yaml.YAMLError):
                return WorkflowConfig()
        return WorkflowConfig()

    def save_config(self):
        config_data = self.config.dict()
        try:
            if self.config_path.suffix == '.json':
                with open(self.config_path, 'w') as f:
                    json.dump(config_data, f, indent=2)
            else:
                with open(self.config_path, 'w') as f:
                    yaml.dump(config_data, f)
        except IOError as e:
            log_activity("Config save error", str(e), "ERROR")


# =============================================================================
# FONCTIONS DE BASE ET UTILITAIRES
# =============================================================================

def ensure_memory_directory():
    """Crée le répertoire de mémoire s'il n'existe pas"""
    try:
        MEMORY_DIR.mkdir(exist_ok=True)
        WORKSPACE_SNAPSHOTS_DIR.mkdir(exist_ok=True)
    except OSError as e:
        print(f"Erreur lors de la création du répertoire mémoire : {e}", file=sys.stderr)
        sys.exit(1)


def setup_logging(level: str = "INFO"):
    """Configure le système de logging"""
    ensure_memory_directory()
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(ACTIVITY_LOG),
            logging.StreamHandler() if not BACKGROUND_MODE else logging.NullHandler()
        ]
    )
    return logging.getLogger("jules_workflow")


def log_activity(action: str, details: str = "", level: str = "INFO"):
    """Journalise les activités dans le fichier de log"""
    logger = setup_logging()
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(f"{action}: {details}")


def load_memory() -> Dict[str, Any]:
    """Charge la mémoire depuis le fichier JSON"""
    ensure_memory_directory()
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            log_activity("Memory load error", "Fichier de mémoire corrompu. Réinitialisation.", "ERROR")
            return {"projects": {}, "preferences": {}, "solutions": {}}
    return {"projects": {}, "preferences": {}, "solutions": {}}


def save_memory(memory_data: Dict[str, Any]):
    """Sauvegarde la mémoire dans le fichier JSON"""
    ensure_memory_directory()
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory_data, f, indent=2)
        log_activity("Mémoire sauvegardée", "État actuel du système enregistré")
    except IOError:
        log_activity("Memory save error", "Impossible d'écrire dans le fichier mémoire.", "ERROR")


def recall_memory(keyword: str) -> List[Any]:
    """Rappelle les souvenirs pertinents basés sur un mot-clé"""
    memory = load_memory()
    results = []
    keyword_lower = keyword.lower()

    for project_name, project_data in memory.get("projects", {}).items():
        if keyword_lower in project_name.lower():
            results.append({"type": "project", "data": project_data})
        for key, value in project_data.items():
            if isinstance(value, str) and keyword_lower in value.lower():
                results.append({"type": "project_detail", "project": project_name, "key": key, "value": value})

    for solution_name, solution_data in memory.get("solutions", {}).items():
        if keyword_lower in solution_name.lower() or any(
                keyword_lower in str(v).lower() for v in solution_data.values() if isinstance(v, str)
        ):
            results.append({"type": "solution", "data": solution_data})

    return results


def get_reminders() -> List[str]:
    """Récupère les rappels depuis le fichier de reminders"""
    ensure_memory_directory()
    if REMINDERS_FILE.exists():
        try:
            with open(REMINDERS_FILE, "r") as f:
                return [line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")]
        except Exception as e:
            log_activity("Reminders load error", str(e), "ERROR")
    return []


def add_reminder(reminder: str):
    """Ajoute un rappel"""
    ensure_memory_directory()
    try:
        with open(REMINDERS_FILE, "a") as f:
            f.write(f"{datetime.now().isoformat()}: {reminder}\n")
        log_activity("Reminder added", reminder)
    except Exception as e:
        log_activity("Reminder add error", str(e), "ERROR")


def check_reminders():
    """Vérifie et affiche les rappels"""
    reminders = get_reminders()
    if reminders and not BACKGROUND_MODE:
        print("\n🔔 RAPPELS:")
        for i, reminder in enumerate(reminders, 1):
            print(f"  {i}. {reminder}")
        print()


# =============================================================================
# GESTIONNAIRES SPÉCIALISÉS
# =============================================================================

class CacheManager:
    """Gestionnaire de cache pour optimiser les performances"""
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                cached_value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return cached_value
                else:
                    del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        with self.lock:
            self.cache[key] = (value, time.time())

    def clear(self):
        with self.lock:
            self.cache.clear()


class PerformanceMonitor:
    """Moniteur de performances pour les fonctions"""
    def __init__(self):
        self.metrics = {}
        self.lock = threading.Lock()

    def monitor(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            process = psutil.Process()
            start_memory = process.memory_info().rss

            result = func(*args, **kwargs)

            end_memory = process.memory_info().rss
            end_time = time.perf_counter()

            execution_time = end_time - start_time
            memory_used = end_memory - start_memory

            with self.lock:
                self.metrics[func.__name__] = {
                    'execution_time': execution_time,
                    'memory_used_bytes': memory_used,
                    'timestamp': time.time()
                }
            return result
        return wrapper

    def get_metrics(self) -> Dict[str, Any]:
        with self.lock:
            return self.metrics.copy()


class CodeValidator:
    """Valide la syntaxe et les dépendances du code"""
    @staticmethod
    def validate_python_syntax(file_path: str) -> Tuple[bool, List[str]]:
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                ast.parse(f.read())
        except SyntaxError as e:
            errors.append(f"SyntaxError: {e.msg} at line {e.lineno}")
        except Exception as e:
            errors.append(f"Error: {e}")
        return not errors, errors

    @staticmethod
    def run_pylint(file_path: str) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pylint', file_path],
                capture_output=True, text=True, timeout=60, check=False
            )
            return result.returncode == 0, result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return True, "Pylint non disponible ou a expiré."


class BackupManager:
    """Gestionnaire de sauvegardes automatiques"""
    def __init__(self, backup_dir: str = "backups", max_backups: int = 5):
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self, source_dir: str, backup_name: str = None) -> Optional[str]:
        source_path = Path(source_dir)
        if not source_path.is_dir():
            return None

        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_path = self.backup_dir / backup_name
        try:
            shutil.copytree(source_path, backup_path)
            self._cleanup_old_backups()
            return str(backup_path)
        except (IOError, shutil.Error) as e:
            log_activity("Backup error", str(e), "ERROR")
            return None

    def _cleanup_old_backups(self):
        try:
            backups = sorted(self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime)
            while len(backups) > self.max_backups:
                old_backup = backups.pop(0)
                shutil.rmtree(old_backup)
        except OSError as e:
            log_activity("Backup cleanup error", str(e), "ERROR")


class DiagnosticManager:
    """Gestionnaire de diagnostics système"""
    def system_health_check(self) -> Dict:
        return {
            'system': platform.system(),
            'python_version': platform.python_version(),
            'disk_usage': self._check_disk_space(),
            'memory_usage': psutil.virtual_memory()._asdict(),
            'dependencies': self._check_dependencies()
        }

    def _check_disk_space(self) -> Dict:
        try:
            usage = shutil.disk_usage("/")
            return {"total": usage.total, "used": usage.used, "free": usage.free}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_dependencies(self) -> Dict[str, bool]:
        dependencies = ['python', 'pip', 'git']
        status = {}
        for dep in dependencies:
            status[dep] = shutil.which(dep) is not None
        return status


class ArchitectureGenerator:
    """Génère des diagrammes d'architecture de code"""
    def generate_class_diagram(self, file_path: str, output_path: str, output_format: str = 'png'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            dot = graphviz.Digraph(comment='Class Diagram', format=output_format)
            dot.attr('node', shape='record')

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
                    label = f"{{ {node.name} | + {'()\\n+'.join(methods)}() }}"
                    dot.node(node.name, label=label)

            dot.render(output_path, view=False, cleanup=True)
            print(f"✅ Diagramme généré: {output_path}.{output_format}")
        except Exception as e:
            print(f"❌ Erreur lors de la génération du diagramme: {e}", file=sys.stderr)


class SecretManager:
    """Gestionnaire de secrets"""
    def __init__(self, key_file: str = '.secret.key'):
        self.key_file = Path(key_file)
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        if self.key_file.exists():
            return self.key_file.read_bytes()
        key = Fernet.generate_key()
        self.key_file.write_bytes(key)
        return key

    def encrypt_secret(self, secret: str) -> str:
        return self.fernet.encrypt(secret.encode()).decode()

    def decrypt_secret(self, encrypted_secret: str) -> Optional[str]:
        try:
            return self.fernet.decrypt(encrypted_secret.encode()).decode()
        except Exception:
            return None


class CognitiveComplexityAnalyzer:
    """Analyse la complexité cognitive du code"""
    def analyze_file(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
        except Exception:
            return {}

        metrics = {'functions': []}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                metrics['functions'].append({'name': node.name, 'complexity': complexity, 'line': node.lineno})
        return metrics

    def _calculate_complexity(self, node: ast.AST) -> int:
        complexity = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        return complexity


class RefactoringAutomator:
    """Automatise des tâches de refactoring simples"""
    def rename_variable(self, code: str, old_name: str, new_name: str) -> str:
        tree = ast.parse(code)
        class VariableRenamer(ast.NodeTransformer):
            def visit_Name(self, node):
                if node.id == old_name:
                    return ast.Name(id=new_name, ctx=node.ctx)
                return node
        new_tree = VariableRenamer().visit(tree)
        return astor.to_source(new_tree)


class DeadCodeDetector:
    """Détecte le code potentiellement mort (fonctions non appelées)"""
    def analyze_project(self, project_path: str) -> List[Dict]:
        all_defs = set()
        all_calls = set()
        files_to_analyze = [p for p in Path(project_path).rglob('*.py')]

        for file_path in files_to_analyze:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        all_defs.add(node.name)
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        all_calls.add(node.func.id)
            except Exception:
                continue

        dead_funcs = all_defs - all_calls
        return [{'type': 'function', 'name': func} for func in dead_funcs if not func.startswith('_')]


class SecurityVulnerabilityScanner:
    """Scan le code pour des vulnérabilités de sécurité basiques"""
    def __init__(self):
        self.patterns = {
            'hardcoded_secrets': r'(password|api[_-]?key|secret)[\s=:].*[\'"][^\'"]{4,}[\'"]'
        }

    def scan_code(self, code: str) -> List[Dict]:
        vulnerabilities = []
        for vuln_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    'type': vuln_type,
                    'line': code[:match.start()].count('\n') + 1,
                    'snippet': match.group(0),
                    'severity': 'high'
                })
        return vulnerabilities


class Dashboard:
    """Gère le tableau de bord web pour visualiser l'activité de Jules."""

    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jules's Dashboard</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; background-color: #f4f4f4; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1, h2 { color: #5a5a5a; }
        .card { background: #f9f9f9; border-left: 5px solid #007bff; margin-bottom: 20px; padding: 15px; }
        pre { white-space: pre-wrap; word-wrap: break-word; background: #eee; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tableau de Bord de Jules</h1>
        <div class="card">
            <h2> Rappels </h2>
            <pre>{{ reminders }}</pre>
        </div>
        <div class="card">
            <h2> Activité Récente (Log) </h2>
            <pre>{{ logs }}</pre>
        </div>
    </div>
</body>
</html>
"""

    def __init__(self):
        self.app = Flask(__name__)
        self._setup_routes()

    def _read_logs(self):
        if ACTIVITY_LOG.exists():
            try:
                with open(ACTIVITY_LOG, 'r', encoding='utf-8') as f:
                    # Read last 50 lines
                    lines = f.readlines()
                    return "".join(lines[-50:])
            except IOError:
                return "Erreur de lecture du fichier de log."
        return "Le fichier de log est vide ou n'existe pas."

    def _read_reminders(self):
        return "\n".join(get_reminders()) or "Aucun rappel."

    def _setup_routes(self):
        @self.app.route('/')
        def home():
            logs = self._read_logs()
            reminders = self._read_reminders()
            return render_template_string(self.HTML_TEMPLATE, logs=logs, reminders=reminders)

    def run(self, host='127.0.0.1', port=5000):
        print(f"INFO: Dashboard disponible sur http://{host}:{port}")
        self.app.run(host=host, port=port)


# =============================================================================
# FONCTIONS PRINCIPALES DE WORKFLOW
# =============================================================================

def generate_tests_for_file(file_path: str):
    """Génère un squelette de tests unitaires pour un fichier Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        test_file_name = f"test_{Path(file_path).name}"
        test_file_path = Path(file_path).parent / test_file_name

        test_content = [
            "import pytest",
            f"from {Path(file_path).stem} import *", ""
        ]

        for node in tree.body: # Iterate over top-level nodes
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                test_content.extend([
                    f"def test_{node.name}():",
                    f"    # TODO: Implémenter le test pour {node.name}",
                    f"    assert False", ""
                ])
            elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and not method.name.startswith('_'):
                        test_content.extend([
                            f"def test_{node.name}_{method.name}():",
                            f"    # TODO: Implémenter le test pour {node.name}.{method.name}",
                            f"    assert False", ""
                        ])

        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(test_content))
        print(f"✅ Fichier de test généré: {test_file_path}")

    except Exception as e:
        print(f"❌ Erreur lors de la génération des tests: {e}", file=sys.stderr)


def document_file(file_path: str):
    """Génère un squelette de documentation pour un fichier Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        doc_file_name = f"README_{Path(file_path).stem}.md"
        doc_file_path = Path(file_path).parent / doc_file_name

        doc_content = [f"# Documentation pour {Path(file_path).name}\n"]

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                docstring = ast.get_docstring(node) or "Aucune documentation."
                params = [arg.arg for arg in node.args.args]
                doc_content.extend([
                    f"### `{node.name}`",
                    f"**Description:** {docstring}",
                    f"**Paramètres:** `{'`, `'.join(params)}`", ""
                ])

        with open(doc_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(doc_content))
        print(f"✅ Documentation générée: {doc_file_path}")

    except Exception as e:
        print(f"❌ Erreur lors de la génération de documentation: {e}", file=sys.stderr)


def create_new_project(project_name: str, project_type: str):
    """Crée une nouvelle structure de projet"""
    project_path = Path(project_name)
    if project_path.exists():
        print(f"❌ Le projet {project_name} existe déjà.", file=sys.stderr)
        return

    try:
        project_path.mkdir()
        (project_path / "src").mkdir()
        (project_path / "tests").mkdir()
        (project_path / "README.md").write_text(f"# {project_name}\n")
        print(f"✅ Projet {project_name} ({project_type}) créé.")
    except OSError as e:
        print(f"❌ Erreur lors de la création du projet: {e}", file=sys.stderr)


def save_workspace(snapshot_name: str, force: bool = False):
    """Sauvegarde l'état de l'espace de travail (mémoire et config)"""
    snapshot_path = WORKSPACE_SNAPSHOTS_DIR / f"{snapshot_name}.tar.gz"
    if snapshot_path.exists() and not force:
        print(f"❌ Snapshot {snapshot_name} existe. Utilisez --force.", file=sys.stderr)
        return

    try:
        with tarfile.open(snapshot_path, "w:gz") as tar:
            if MEMORY_DIR.exists():
                tar.add(MEMORY_DIR, arcname=MEMORY_DIR.name)
        print(f"✅ Snapshot sauvegardé: {snapshot_path}")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}", file=sys.stderr)


def load_workspace(snapshot_name: str):
    """Restaure un snapshot d'espace de travail"""
    snapshot_path = WORKSPACE_SNAPSHOTS_DIR / f"{snapshot_name}.tar.gz"
    if not snapshot_path.exists():
        print(f"❌ Snapshot introuvable: {snapshot_name}", file=sys.stderr)
        return

    try:
        if MEMORY_DIR.exists():
            shutil.rmtree(MEMORY_DIR)
        with tarfile.open(snapshot_path, "r:gz") as tar:
            tar.extractall(path=".")
        print(f"✅ Snapshot restauré: {snapshot_name}")
    except Exception as e:
        print(f"❌ Erreur lors de la restauration: {e}", file=sys.stderr)


# =============================================================================
# GESTION DU DÉMON
# =============================================================================

def cleanup_pid_file():
    """Supprime le fichier PID s'il existe."""
    if PID_FILE.exists():
        PID_FILE.unlink()

def signal_handler(sig, frame):
    """Gestionnaire de signaux pour un arrêt propre."""
    print("\nArrêt en cours...", file=sys.stderr)
    cleanup_pid_file()
    sys.exit(0)

def daemon_loop(config: WorkflowConfig):
    """Boucle principale du démon."""
    # Setup signal handler for the daemon process
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            check_reminders()
            # cleanup_old_snapshots(config.auto_cleanup_days)
            time.sleep(DAEMON_CHECK_INTERVAL)
        except Exception as e:
            log_activity("Erreur boucle démon", str(e), "ERROR")

def start_daemon():
    """Lance le démon en tant que processus détaché en utilisant le script runner."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            if psutil.pid_exists(pid):
                print(f"❌ Démon déjà en cours d'exécution (PID: {pid}).", file=sys.stderr)
                sys.exit(1)
        except (IOError, ValueError):
            pass  # Fichier PID obsolète, on continue

    runner_script_path = SCRIPT_DIR / "jules_daemon_runner.py"
    command = [sys.executable, str(runner_script_path)]

    # Lancer en tant que processus complètement détaché
    subprocess.Popen(command, close_fds=True, start_new_session=True)

    print(f"✅ Commande de démarrage du démon envoyée.")
    time.sleep(1) # Laisser le temps au démon de démarrer et d'écrire le PID


def stop_daemon():
    """Arrête le processus du démon en lisant le fichier PID."""
    if not PID_FILE.exists():
        print("❌ Démon inactif (aucun fichier PID).", file=sys.stderr)
        return

    try:
        pid = int(PID_FILE.read_text())
    except (IOError, ValueError):
        print("❌ Fichier PID invalide. Nettoyage...", file=sys.stderr)
        cleanup_pid_file()
        return

    try:
        p = psutil.Process(pid)
        p.terminate()  # Envoie SIGTERM
        try:
            p.wait(timeout=3)
        except psutil.TimeoutExpired:
            p.kill()  # Envoie SIGKILL
        print(f"✅ Démon (PID: {pid}) arrêté avec succès.")
    except psutil.NoSuchProcess:
        print(f"❌ Aucun processus trouvé avec le PID {pid}. Nettoyage.", file=sys.stderr)
    except Exception as e:
        print(f"❌ Erreur lors de l'arrêt du démon: {e}", file=sys.stderr)
    finally:
        cleanup_pid_file()

# =============================================================================
# FONCTION PRINCIPALE (CLI)
# =============================================================================

def main():
    """Fonction principale du système de workflow."""
    config_manager = ConfigManager()
    config = config_manager.load_config()

    parser = argparse.ArgumentParser(description="Système de Workflow Automatisé pour Jules")
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles", required=True)

    # Commandes de base
    subparsers.add_parser("recall", help="Rechercher dans la mémoire").add_argument("keyword")
    subparsers.add_parser("add-reminder", help="Ajouter un rappel").add_argument("reminder", type=str)
    subparsers.add_parser("health", help="Vérifier la santé du système")

    # Commandes de projet
    project_parser = subparsers.add_parser("new-project", help="Créer un nouveau projet")
    project_parser.add_argument("name")
    project_parser.add_argument("--type", default=config.default_project_type)

    # Commandes de génération de code
    gen_parser = subparsers.add_parser("generate", help="Générer du code ou des documents")
    gen_sub = gen_parser.add_subparsers(dest="what", required=True)
    gen_sub.add_parser("tests", help="Générer des tests").add_argument("file", type=str)
    gen_sub.add_parser("docs", help="Générer de la documentation").add_argument("file", type=str)
    arch_parser = gen_sub.add_parser("arch-diagram", help="Générer un diagramme de classes")
    arch_parser.add_argument("file", type=str)
    arch_parser.add_argument("output", type=str)

    # Commandes d'analyse
    analyze_parser = subparsers.add_parser("analyze", help="Analyser le code")
    analyze_sub = analyze_parser.add_subparsers(dest="what", required=True)
    analyze_sub.add_parser("validate", help="Valider la syntaxe").add_argument("file", type=str)
    analyze_sub.add_parser("complexity", help="Analyser la complexité").add_argument("file", type=str)
    analyze_sub.add_parser("dead-code", help="Détecter le code mort").add_argument("path", type=str)
    analyze_sub.add_parser("security", help="Scanner les vulnérabilités").add_argument("file", type=str)

    # Commandes de workspace
    ws_parser = subparsers.add_parser("workspace", help="Gérer l'espace de travail")
    ws_sub = ws_parser.add_subparsers(dest="action", required=True)
    save_parser = ws_sub.add_parser("save", help="Sauvegarder le workspace")
    save_parser.add_argument("name")
    save_parser.add_argument("--force", action="store_true")
    ws_sub.add_parser("load", help="Restaurer le workspace").add_argument("name")

    # Commande Dashboard
    subparsers.add_parser("dashboard", help="Lancer le tableau de bord web")

    # Commandes du démon
    daemon_parser = subparsers.add_parser("daemon", help="Gérer le mode démon")
    daemon_group = daemon_parser.add_mutually_exclusive_group(required=True)
    daemon_group.add_argument("--start", action="store_true")
    daemon_group.add_argument("--stop", action="store_true")
    daemon_group.add_argument("--status", action="store_true")

    args = parser.parse_args()

    # Logique d'exécution
    if args.command == "daemon":
        if args.start:
            start_daemon()
        elif args.stop:
            stop_daemon()
        elif args.status:
            if PID_FILE.exists():
                try:
                    pid = int(PID_FILE.read_text())
                    if psutil.pid_exists(pid):
                        print(f"✅ Démon actif (PID: {pid})")
                    else:
                        print("❌ Démon inactif (fichier PID obsolète). Nettoyage...")
                        cleanup_pid_file()
                except (IOError, ValueError):
                    print("❌ Démon inactif (fichier PID invalide). Nettoyage...")
                    cleanup_pid_file()
            else:
                print("❌ Démon inactif")
    elif args.command == "recall":
        print(json.dumps(recall_memory(args.keyword), indent=2))
    elif args.command == "add-reminder":
        add_reminder(args.reminder)
        print("✅ Rappel ajouté.")
    elif args.command == "health":
        print(json.dumps(DiagnosticManager().system_health_check(), indent=2))
    elif args.command == "new-project":
        create_new_project(args.name, args.type)
    elif args.command == "generate":
        if args.what == "tests":
            generate_tests_for_file(args.file)
        elif args.what == "docs":
            document_file(args.file)
        elif args.what == "arch-diagram":
            ArchitectureGenerator().generate_class_diagram(args.file, args.output)
    elif args.command == "analyze":
        if args.what == "validate":
            ok, errors = CodeValidator.validate_python_syntax(args.file)
            print(f"Syntaxe OK: {ok}\nErreurs: {errors}")
        elif args.what == "complexity":
            print(json.dumps(CognitiveComplexityAnalyzer().analyze_file(args.file), indent=2))
        elif args.what == "dead-code":
            print(json.dumps(DeadCodeDetector().analyze_project(args.path), indent=2))
        elif args.what == "security":
            with open(args.file, 'r') as f:
                code = f.read()
            print(json.dumps(SecurityVulnerabilityScanner().scan_code(code), indent=2))
    elif args.command == "workspace":
        if args.action == "save":
            save_workspace(args.name, args.force)
        elif args.action == "load":
            load_workspace(args.name)
    elif args.command == "dashboard":
        Dashboard().run()

if __name__ == "__main__":
    ensure_memory_directory()
    main()
