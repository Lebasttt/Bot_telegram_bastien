#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Runner script for the Jules Performance Daemon.
This script contains the logic to run the performance optimization loop.
"""

import os
import sys
import time
import signal
import logging
import psutil
import gc
import json
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PID_FILE = SCRIPT_DIR / ".jules_performance_daemon.pid"
LOG_FILE = SCRIPT_DIR / "logs/performance_daemon.log"
MEMORY_DIR = SCRIPT_DIR / ".jules_memory" # To align with other scripts
ACTIVITY_LOG = MEMORY_DIR / "activity.log"

# =============================================================================
# DAEMON LOGIC (Adapted from raw file)
# =============================================================================

class PerformanceDaemon:
    """A simplified version of the daemon for the runner script."""

    def __init__(self, memory_threshold=75, cpu_threshold=80, check_interval=30):
        self.memory_threshold = memory_threshold
        self.cpu_threshold = cpu_threshold
        self.check_interval = check_interval
        self.is_running = False
        self.setup_logging()

    def setup_logging(self):
        """Sets up logging for the daemon process."""
        LOG_FILE.parent.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger("PerformanceDaemon")

    def monitor_system_health(self):
        """Monitors system health and logs it."""
        memory = psutil.virtual_memory()
        cpu_usage = psutil.cpu_percent(interval=1)
        self.logger.info(f"Health Check: MEM={memory.percent}%, CPU={cpu_usage}%")
        return memory.percent, cpu_usage

    def optimize_memory(self, memory_usage):
        """Performs memory optimization if threshold is crossed."""
        if memory_usage > self.memory_threshold:
            self.logger.warning(f"Memory threshold crossed ({memory_usage}%). Optimizing...")
            gc.collect()
            self.logger.info("Memory optimization (gc.collect) complete.")

    def optimize_cpu(self, cpu_usage):
        """Performs CPU throttling if threshold is crossed."""
        if cpu_usage > self.cpu_threshold:
            self.logger.warning(f"CPU threshold crossed ({cpu_usage}%). Throttling...")
            time.sleep(1) # Simple throttle
            self.logger.info("CPU throttling complete.")

    def graceful_shutdown(self, signum, frame):
        """Handles shutdown signals."""
        self.logger.info("Shutdown signal received. Exiting gracefully.")
        self.is_running = False

    def run_daemon(self):
        """The main loop for the daemon."""
        self.is_running = True
        self.logger.info(f"Performance daemon started with PID {os.getpid()}.")

        signal.signal(signal.SIGINT, self.graceful_shutdown)
        signal.signal(signal.SIGTERM, self.graceful_shutdown)

        while self.is_running:
            try:
                mem_percent, cpu_percent = self.monitor_system_health()
                self.optimize_memory(mem_percent)
                self.optimize_cpu(cpu_percent)
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Error in daemon loop: {e}", exc_info=True)
                time.sleep(self.check_interval) # Prevent fast crash loop

# =============================================================================
# DAEMON ENTRY POINT
# =============================================================================

def cleanup_pid_file():
    """Ensures the PID file is removed on exit."""
    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except OSError:
            pass

if __name__ == "__main__":
    # Write PID file
    try:
        PID_FILE.write_text(str(os.getpid()))
    except IOError as e:
        sys.exit(f"CRITICAL: Could not write PID file to {PID_FILE}. Error: {e}")

    # Register cleanup
    import atexit
    atexit.register(cleanup_pid_file)

    # Instantiate and run the daemon
    # In a real scenario, these would come from a config file
    daemon = PerformanceDaemon(
        memory_threshold=75,
        cpu_threshold=80,
        check_interval=30
    )
    daemon.run_daemon()
