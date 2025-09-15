#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Système de Performance et d'Optimisation - Agent Principal
Version complète et intégrée
"""

import sys
import os
import argparse
import psutil
from pathlib import Path
import subprocess
import time
import json
import re
import gc
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PID_FILE = SCRIPT_DIR / ".jules_performance_daemon.pid"
MEMORY_DIR = SCRIPT_DIR / ".jules_memory"
CONFIG_FILE = MEMORY_DIR / "performance_config.json"

# =============================================================================
# CORE CLASSES
# =============================================================================

class MemorySystem:
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.memory_db = self.memory_dir / "performance_memory.json"
        self.activity_log = self.memory_dir / "activity.log"
        self.ensure_memory_dir()

    def ensure_memory_dir(self):
        self.memory_dir.mkdir(exist_ok=True)

    def load_memory(self) -> Dict:
        try:
            if self.memory_db.exists():
                with open(self.memory_db, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erreur chargement mémoire: {e}")
        return {"knowledge": {}, "activities": []}

    def save_memory(self, data: Dict):
        try:
            with open(self.memory_db, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde mémoire: {e}")

    def log_activity(self, activity_type: str, description: str, details: Dict = None):
        memory_data = self.load_memory()
        activity = {
            "timestamp": datetime.now().isoformat(), "type": activity_type,
            "description": description, "details": details or {}
        }
        activities = memory_data.setdefault("activities", [])
        activities.append(activity)
        memory_data["activities"] = activities[-1000:]
        self.save_memory(memory_data)
        with open(self.activity_log, 'a', encoding='utf-8') as f:
            f.write(f"{activity['timestamp']} - PERF - {activity_type}: {description}\n")

class WorkflowTools:
    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

    def get_git_commits(self, since: str = "main") -> List[Dict]:
        try:
            result = subprocess.run(
                ["git", "log", f"{since}..HEAD", "--oneline", "--pretty=format:%h|%s"],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        commits.append({"hash": parts[0], "message": parts[1]})
            return commits
        except Exception as e:
            print(f"Erreur récupération commits: {e}")
            return []

    def generate_pull_request(self, base_branch: str = "main", output_file: str = "PULL_REQUEST.md"):
        commits = self.get_git_commits(base_branch)
        if not commits:
            print("Aucun commit trouvé depuis la branche", base_branch)
            return
        changes = "\n".join([f"- {c['message']} ({c['hash']})" for c in commits])
        pr_content = f"# Pull Request\n\n## Changements\n{changes}"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pr_content)
        self.memory.log_activity("pr_generated", f"PR générée pour {len(commits)} commits")
        print(f"✅ PR générée: {output_file}")


class IntelligentDiagnostic:
    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.patterns = self.load_diagnostic_patterns()

    def load_diagnostic_patterns(self):
        return {
            "high_memory": {"symptoms": ["memory_percent > 85"], "solution": "High memory usage detected. Consider profiling memory allocations."},
            "high_cpu": {"symptoms": ["cpu_usage > 90"], "solution": "CPU usage is very high. Check for runaway processes or optimize hot paths."}
        }

    def run_diagnostic(self):
        health_data = {"memory_percent": psutil.virtual_memory().percent, "cpu_usage": psutil.cpu_percent(interval=1)}
        issues = []
        for issue_name, pattern in self.patterns.items():
            if self._check_pattern(health_data, pattern):
                issues.append({"type": issue_name, "solution": pattern["solution"]})
        if issues:
            self.memory.log_activity("diagnostic_completed", f"Diagnostic found {len(issues)} issues", {"issues": issues})
        return issues

    def _check_pattern(self, health_data, pattern):
        for symptom in pattern["symptoms"]:
            match = re.match(r"(\w+)\s*([><=]+)\s*([\d\.]+)", symptom)
            if not match: continue
            metric, operator, value = match.groups()
            value = float(value)
            actual_value = health_data.get(metric)
            if actual_value is None: continue
            if operator == '>' and not (actual_value > value): return False
            if operator == '<' and not (actual_value < value): return False
        return True

# =============================================================================
# DAEMON CONTROL AND MAIN CLI
# =============================================================================

def start_daemon():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            if psutil.pid_exists(pid):
                print(f"❌ Daemon de performance déjà en cours (PID: {pid}).")
                return
        except (IOError, ValueError, psutil.Error):
            PID_FILE.unlink()
    runner_script_path = SCRIPT_DIR / "performance_daemon_runner.py"
    command = [sys.executable, str(runner_script_path)]
    subprocess.Popen(command, close_fds=True, start_new_session=True)
    print("✅ Commande de démarrage du daemon de performance envoyée.")
    time.sleep(1)

def stop_daemon():
    if not PID_FILE.exists():
        print("❌ Daemon de performance inactif (aucun fichier PID).")
        return
    try:
        pid = int(PID_FILE.read_text())
        p = psutil.Process(pid)
        p.terminate()
        p.wait(timeout=3)
    except (psutil.NoSuchProcess, ValueError, IOError, psutil.TimeoutExpired):
        pass
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()
        print(f"✅ Daemon de performance arrêté.")

def get_status():
    if not PID_FILE.exists():
        print("❌ Daemon de performance inactif.")
        return
    try:
        pid = int(PID_FILE.read_text())
        if psutil.pid_exists(pid):
            print(f"✅ Daemon de performance actif (PID: {pid}).")
        else:
            print("❌ Daemon de performance inactif (fichier PID obsolète).")
            PID_FILE.unlink()
    except (IOError, ValueError):
        print("❌ Daemon de performance inactif (fichier PID invalide).")
        if PID_FILE.exists():
            PID_FILE.unlink()

def main():
    parser = argparse.ArgumentParser(description="Agent de Performance et d'Optimisation")
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")
    subparsers.required = True

    daemon_parser = subparsers.add_parser("daemon", help="Gérer le mode démon")
    daemon_group = daemon_parser.add_mutually_exclusive_group(required=True)
    daemon_group.add_argument("--start", action="store_true")
    daemon_group.add_argument("--stop", action="store_true")
    daemon_group.add_argument("--status", action="store_true")

    subparsers.add_parser("diagnose", help="Exécuter un diagnostic complet")
    subparsers.add_parser("create-pr", help="Générer une description de PR")

    args = parser.parse_args()

    memory_system = MemorySystem()

    if args.command == "daemon":
        if args.start: start_daemon()
        elif args.stop: stop_daemon()
        elif args.status: get_status()
    elif args.command == "diagnose":
        diagnostic = IntelligentDiagnostic(memory_system)
        issues = diagnostic.run_diagnostic()
        if issues:
            print("Problèmes de diagnostic trouvés:")
            for issue in issues:
                print(f"- {issue['type']}: {issue['solution']}")
        else:
            print("Aucun problème de diagnostic trouvé.")
    elif args.command == "create-pr":
        workflow_tools = WorkflowTools(memory_system)
        workflow_tools.generate_pull_request()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
