import os
import sys
import time
import atexit
import signal

# --- Dépendances inter-modules ---
from .core.config import CONFIG

PID_FILE = CONFIG.get("PID_FILE")

def write_pid_file():
    """Écrit le PID du processus courant dans le fichier PID."""
    if not PID_FILE:
        print("ERREUR: PID_FILE n'est pas configuré.", file=sys.stderr)
        return
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except IOError as e:
        print(f"ERREUR: Impossible d'écrire dans le fichier PID {PID_FILE}: {e}", file=sys.stderr)
        sys.exit(1)

def stop_daemon_process() -> bool:
    """Arrête le processus daemon en lisant le PID et en envoyant un signal SIGTERM."""
    if not PID_FILE or not os.path.exists(PID_FILE):
        print("Aucun fichier PID trouvé. Le daemon n'est probablement pas en cours d'exécution.")
        return False

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
    except (IOError, ValueError) as e:
        print(f"Erreur lors de la lecture du fichier PID: {e}")
        return False

    try:
        # Envoyer SIGTERM pour un arrêt propre
        os.kill(pid, signal.SIGTERM)
        print(f"Signal SIGTERM envoyé au processus daemon (PID: {pid}).")
        # Attendre un peu pour que le processus se termine
        time.sleep(2)
        # Vérifier si le processus est toujours en cours
        os.kill(pid, 0) # Lève une exception si le processus n'existe pas
        print("Le processus ne s'est pas arrêté. Tenter avec SIGKILL.")
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        print("Le processus daemon s'est arrêté avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'arrêt du processus: {e}")
        return False
    finally:
        # Nettoyer le fichier PID
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

    return True

def daemonize():
    """
    Transforme le processus courant en daemon en utilisant la technique du double fork.
    """
    if os.path.exists(PID_FILE):
        print("Le fichier PID existe déjà. Le daemon est-il déjà en cours d'exécution ?", file=sys.stderr)
        sys.exit(1)

    # Premier fork pour se détacher du parent
    try:
        if os.fork() > 0:
            sys.exit(0) # Le parent quitte
    except OSError as e:
        sys.stderr.write(f"Premier fork échoué: {e}\n")
        sys.exit(1)

    # Se détacher de l'environnement du parent
    os.chdir(CONFIG.get("SANDBOX_PATH", "/"))
    os.setsid()
    os.umask(0)

    # Second fork pour empêcher le processus de réacquérir un terminal
    try:
        if os.fork() > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"Second fork échoué: {e}\n")
        sys.exit(1)

    # Rediriger les descripteurs de fichiers standards
    sys.stdout.flush()
    sys.stderr.flush()
    with open(os.devnull, 'rb') as f_read, open(os.devnull, 'ab') as f_write:
        os.dup2(f_read.fileno(), sys.stdin.fileno())
        os.dup2(f_write.fileno(), sys.stdout.fileno())
        os.dup2(f_write.fileno(), sys.stderr.fileno())

    # Écrire le fichier PID
    write_pid_file()

    # Enregistrer un gestionnaire pour le nettoyage à la sortie
    def at_exit():
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

    atexit.register(at_exit)
