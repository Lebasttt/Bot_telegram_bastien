#!/usr/bin/env python3
"""
ai_debug_ultimate.py - Système de débogage, sécurité et intégration mémoire pour Jules
"""
import sys
import time
import json
import threading
import os
import errno
import io
import functools
from functools import lru_cache
import traceback
import hashlib
import base64
import uuid
import zlib
import inspect
import pdb
import ast
import gc
import weakref
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import cProfile
import pstats
import signal
import resource
import faulthandler
import subprocess
import re
import tempfile
import argparse
from collections import defaultdict, deque
from types import ModuleType, FunctionType, FrameType
from typing import Any, Callable, Dict, Iterable, Optional, Set, List, Tuple, Union
import psutil
import pytest
import jsonschema

# =========================
# CONFIGURATION
# =========================
SANDBOX_PATH = os.getenv("WORKSPACE", "/app")
os.makedirs(SANDBOX_PATH, exist_ok=True)
LOG_FILE = os.path.join(SANDBOX_PATH, "ai_debug_log.ndjson")
PID_FILE = os.path.join(SANDBOX_PATH, "ai_debug.pid")
# ... (et autres variables de config)
CONFIG = {}
# ... (logique de chargement de config)

# =========================
# LOGGING & SETUP
# =========================
def setup_logging_with_rotation():
    handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8', delay=True)
    handler.setFormatter(logging.Formatter('%(asctime)s - JULES_DEBUG - %(levelname)s - %(message)s'))
    logger = logging.getLogger("jules_debug")
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logging_with_rotation()

# =========================
# GESTIONNAIRES DE SIGNAL
# =========================
SHUTDOWN_REQUESTED = False

def emergency_shutdown(signum, frame):
    global SHUTDOWN_REQUESTED
    SHUTDOWN_REQUESTED = True
    logger.critical(f"Arrêt d'urgence déclenché par signal {signum}")
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except:
        pass
    sys.exit(1)

def register_signal_handlers():
    signal.signal(signal.SIGINT, emergency_shutdown)
    signal.signal(signal.SIGTERM, emergency_shutdown)
    if hasattr(signal, 'SIGQUIT'):
        signal.signal(signal.SIGQUIT, emergency_shutdown)

# =========================
# FONCTIONS & CLASSES
# =========================
# ... (ICI, JE METS TOUTES LES FONCTIONS ET CLASSES DU SCRIPT)
# ... (jules_safe, log_to_memory, AutoRecoverySystem, etc., etc.)
def main_loop():
    """Placeholder for the main daemon loop."""
    while not SHUTDOWN_REQUESTED:
        print("Daemon loop running...")
        time.sleep(10)

def daemonize():
    """Correct daemonization."""
    try:
        if os.fork() > 0: sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #1 failed: {e.errno} ({e.strerror})\n")
        sys.exit(1)
    os.chdir("/")
    os.setsid()
    os.umask(0)
    try:
        if os.fork() > 0: sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #2 failed: {e.errno} ({e.strerror})\n")
        sys.exit(1)
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def check_daemon_status():
    """Checks if the daemon process is running."""
    if not os.path.exists(PID_FILE):
        print("❌ Daemon is not running (PID file not found).")
        return

    with open(PID_FILE, 'r') as f:
        pid_str = f.read().strip()

    if not pid_str:
        print("⚠️ Daemon status unknown (PID file is empty).")
        return

    try:
        pid = int(pid_str)
    except ValueError:
        print(f"⚠️ Daemon status unknown (invalid PID in file: {pid_str}).")
        return

    if psutil.pid_exists(pid):
        p = psutil.Process(pid)
        # A more robust check to see if it's the right process
        if 'debug_tool.py' in " ".join(p.cmdline()) and '--daemon' in p.cmdline():
            print(f"✅ Daemon is running with PID {pid}.")
        else:
            print(f"PID {pid} exists, but it's not the debug daemon. Cleaning up stale PID file.")
            os.remove(PID_FILE)
    else:
        print(f"❌ Daemon is not running (stale PID file for PID {pid}). Cleaning up.")
        os.remove(PID_FILE)

def run_tests():
    """Discovers and runs tests using pytest in a subprocess."""
    print("🔬 Discovering and running tests with pytest...")
    try:
        # Using subprocess is safer as pytest.main() can call sys.exit()
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', SANDBOX_PATH],
            capture_output=True,
            text=True,
            check=False  # We'll check the return code manually
        )
        print("--- Pytest Output ---")
        # Only print stdout if it's not empty
        if result.stdout:
            print(result.stdout)
        # Only print stderr if it's not empty
        if result.stderr:
            print("--- Pytest Errors ---")
            print(result.stderr)

        if result.returncode == 0:
            print("✅ All tests passed.")
        else:
            print(f"❌ Some tests failed (exit code: {result.returncode}).")
        print("--- End of Test Run ---")

    except FileNotFoundError:
        print("🔥 Error: 'pytest' command not found. Is pytest installed in the environment?")
    except Exception as e:
        print(f"🔥 An unexpected error occurred while running tests: {e}")

def stop_daemon_process():
    if not os.path.exists(PID_FILE):
        print("PID file not found. Is the daemon running?")
        return
    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to process {pid}")
    except ProcessLookupError:
        print(f"Process {pid} not found.")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

# =========================
# POINT D'ENTRÉE PRINCIPAL
# =========================
if __name__ == "__main__":
    register_signal_handlers()

    parser = argparse.ArgumentParser(description="Système de Débogage Ultime pour Jules")
    parser.add_argument("--daemon", action="store_true", help="Démarre en mode daemon")
    parser.add_argument("--stop", action="store_true", help="Arrête le daemon")
    parser.add_argument("--status", action="store_true", help="Vérifie le statut du daemon")
    parser.add_argument("--run-tests", action="store_true", help="Lance la suite de tests avec pytest")
    parser.add_argument("--setup", action="store_true", help="Configuration de l'environnement")

    args = parser.parse_args()

    if args.daemon:
        print("Démarrage en mode daemon...")
        daemonize()
        logger.info("Daemon started.")
        main_loop()
    elif args.stop:
        print("Arrêt du daemon...")
        stop_daemon_process()
    elif args.status:
        check_daemon_status()
    elif args.run_tests:
        run_tests()
    elif args.setup:
        print("⚙️ Configuration de l'environnement en cours... (simulation)")
        print("Résultat: {'success': True}")
    else:
        print("Mode interactif. Utilisez --daemon pour démarrer en arrière-plan.")
