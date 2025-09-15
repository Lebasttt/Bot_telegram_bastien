#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Runner script for the Jules Workflow Daemon.
This script contains only the logic necessary to run the daemon loop.
It is launched by the main jules_workflow.py script.
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path
import psutil
import yaml
import json
from pydantic import BaseModel, Field
from datetime import datetime

# =============================================================================
# CONFIGURATION (Mirrored from jules_workflow.py)
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
MEMORY_DIR = SCRIPT_DIR / ".jules_memory"
ACTIVITY_LOG = MEMORY_DIR / "activity.log"
REMINDERS_FILE = MEMORY_DIR / "reminders.md"
PID_FILE = MEMORY_DIR / "daemon.pid"
DAEMON_CHECK_INTERVAL = 60
BACKGROUND_MODE = True # This process is always in background mode

# =============================================================================
# CLASSES DE CONFIGURATION (Needed for the loop)
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
                with open(self.config_path, 'r') as f:
                    data = yaml.safe_load(f)
                return WorkflowConfig(**data)
            except (json.JSONDecodeError, yaml.YAMLError):
                return WorkflowConfig()
        return WorkflowConfig()

# =============================================================================
# DAEMON-SPECIFIC UTILITIES
# =============================================================================

def ensure_memory_directory():
    MEMORY_DIR.mkdir(exist_ok=True)

def setup_logging(level: str = "INFO"):
    ensure_memory_directory()
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(ACTIVITY_LOG),
            logging.NullHandler() # Always use NullHandler for the daemon runner
        ]
    )
    return logging.getLogger("jules_daemon")

def log_activity(action: str, details: str = "", level: str = "INFO"):
    logger = setup_logging()
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(f"{action}: {details}")

def get_reminders() -> list:
    if REMINDERS_FILE.exists():
        try:
            with open(REMINDERS_FILE, "r") as f:
                return [line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")]
        except Exception as e:
            log_activity("Daemon reminders load error", str(e), "ERROR")
    return []

def check_reminders():
    # In daemon mode, we don't print to console. This could be changed to send notifications.
    reminders = get_reminders()
    if reminders:
        log_activity("Reminders checked", f"{len(reminders)} reminders pending.")

def cleanup_pid_file():
    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except OSError:
            pass

def signal_handler(sig, frame):
    log_activity("Daemon shutdown signal received", f"Signal: {sig}")
    cleanup_pid_file()
    sys.exit(0)

def daemon_loop(config: WorkflowConfig):
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    log_activity("Daemon loop started", f"Check interval: {DAEMON_CHECK_INTERVAL}s")
    while True:
        try:
            check_reminders()
            # Placeholder for other daemon tasks
            time.sleep(DAEMON_CHECK_INTERVAL)
        except Exception as e:
            log_activity("Error in daemon loop", str(e), "ERROR")
            time.sleep(DAEMON_CHECK_INTERVAL) # Prevent fast crash loops

# =============================================================================
# DAEMON ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    ensure_memory_directory()

    # Write PID file
    try:
        PID_FILE.write_text(str(os.getpid()))
    except IOError as e:
        # Cannot log yet, so print to stderr if possible
        print(f"DAEMON CRITICAL: Could not write PID file to {PID_FILE}. Exiting. Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Register cleanup
    import atexit
    atexit.register(cleanup_pid_file)

    # Load config and run loop
    config_manager = ConfigManager()
    config = config_manager.load_config()
    setup_logging(config.log_level)

    daemon_loop(config)
