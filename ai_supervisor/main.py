import sys
import argparse
import time
import json
import os

# --- Initialisation de base ---
# Il est crucial d'importer la configuration et le logging en premier.
from .core.config import CONFIG, SANDBOX_PATH
from .core.logging import logger, start_log_writer_thread, stop_log_writer_thread
from .core.exceptions import enable_ultimate_exception_hook

# --- Autres imports de modules ---
from .daemon import daemonize, stop_daemon_process
from .supervisor import UltimateSurveillanceSystem
from .db.database import SurveillanceDatabase
from .security.secret_scanner import scan_for_secrets
from .security.dependency_audit import check_dependencies
from .utils.safe_exec import watch_command

def run_as_daemon():
    """Démonise le processus et lance la surveillance complète."""
    logger.info("Démarrage en mode daemon...")
    daemonize()

    # Le processus parent quitte après le fork, seul le daemon continue ici.
    # Il est important de réinitialiser le logging pour le nouveau processus.
    start_log_writer_thread()
    logger.info(f"Daemon démarré avec PID {os.getpid()}. Logs dans {CONFIG.get('LOG_FILE')}")

    # Initialiser les DBs pour le daemon
    db_process = SurveillanceDatabase(CONFIG.get("PROCESS_DB"))
    db_network = SurveillanceDatabase(CONFIG.get("NETWORK_DB"))
    db_file = SurveillanceDatabase(CONFIG.get("FILE_DB"))
    db_performance = SurveillanceDatabase(CONFIG.get("PERFORMANCE_DB"))

    # Initialiser et lancer le superviseur
    supervisor = UltimateSurveillanceSystem(db_process, db_network, db_file, db_performance)
    supervisor.start_full_surveillance()

    # Boucle infinie pour maintenir le daemon en vie
    try:
        while True:
            time.sleep(3600) # Le travail se fait dans les threads
    except KeyboardInterrupt:
        logger.info("Signal d'arrêt reçu par le daemon.")
    finally:
        supervisor.stop_surveillance()
        stop_log_writer_thread()
        logger.info("Daemon arrêté proprement.")

def main():
    """Point d'entrée principal de l'application."""
    # --- Configuration de l'analyseur d'arguments ---
    parser = argparse.ArgumentParser(description="Système de débogage et de surveillance pour Jules.")
    parser.add_argument("--daemon", action="store_true", help="Lancer le système en mode daemon (arrière-plan).")
    parser.add_argument("--stop", action="store_true", help="Arrêter le daemon en cours d'exécution.")
    parser.add_argument("--scan-for-secrets", action="store_true", help="Lancer un scan de secrets et quitter.")
    parser.add_argument("--check-dependencies", action="store_true", help="Lancer un audit des dépendances et quitter.")
    parser.add_argument("--watch", nargs='+', metavar='CMD', help="Surveiller une commande et quitter.")

    args = parser.parse_args()

    # --- Initialisation des systèmes critiques ---
    # Le logger est déjà initialisé lors de l'import.
    # Démarrer le thread d'écriture des logs pour les opérations synchrones.
    start_log_writer_thread()
    # Activer le gestionnaire d'exceptions global.
    enable_ultimate_exception_hook()

    # --- Exécution basée sur les arguments ---
    try:
        if args.daemon:
            run_as_daemon()
        elif args.stop:
            logger.info("Demande d'arrêt du daemon...")
            if stop_daemon_process():
                logger.info("Daemon arrêté avec succès.")
            else:
                logger.warning("Aucun daemon en cours ou erreur lors de l'arrêt.")
        elif args.scan_for_secrets:
            logger.info("Lancement du scan de secrets...")
            results = scan_for_secrets()
            print(json.dumps(results, indent=2))
            if results.get("secrets_found"):
                sys.exit(1) # Quitter avec un code d'erreur si des secrets sont trouvés
        elif args.check_dependencies:
            logger.info("Lancement de l'audit des dépendances...")
            results = check_dependencies()
            print(json.dumps(results, indent=2))
            if results.get("vulnerabilities"):
                sys.exit(1)
        elif args.watch:
            command_to_watch = " ".join(args.watch)
            logger.info(f"Surveillance de la commande: '{command_to_watch}'")
            result = watch_command(command_to_watch)
            print(json.dumps(result, indent=2))
            if result.get("return_code", 1) != 0:
                sys.exit(1)
        else:
            # Mode interactif (non-daemon)
            logger.info("Démarrage en mode interactif (Ctrl+C pour arrêter).")
            # Initialiser les DBs
            db_process = SurveillanceDatabase(CONFIG.get("PROCESS_DB"))
            db_network = SurveillanceDatabase(CONFIG.get("NETWORK_DB"))
            db_file = SurveillanceDatabase(CONFIG.get("FILE_DB"))
            db_performance = SurveillanceDatabase(CONFIG.get("PERFORMANCE_DB"))

            supervisor = UltimateSurveillanceSystem(db_process, db_network, db_file, db_performance)
            supervisor.start_full_surveillance()

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Arrêt demandé par l'utilisateur.")
            finally:
                supervisor.stop_surveillance()

    except Exception as e:
        logger.critical(f"Une erreur fatale est survenue dans le main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # S'assurer que le thread de log est bien arrêté à la fin
        stop_log_writer_thread()

if __name__ == "__main__":
    main()
