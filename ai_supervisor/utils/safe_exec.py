import subprocess
import os
import time
import threading
import re
import shutil
from typing import Any, Callable, Dict, Optional

# Placeholders pour les dépendances inter-modules
def jules_safe(func): return func
def validate_sandbox_access(path): pass
def log_to_memory(activity, category, importance, metadata=None): pass

# Note: SANDBOX_PATH sera chargé depuis la configuration
SANDBOX_PATH = os.getenv("WORKSPACE", ".")

@jules_safe
def execute_with_timeout(command, timeout=30):
    """Exécute une commande avec timeout et récupération d'erreurs"""
    try:
        # La commande doit être une liste pour Popen/run
        cmd_list = command.split()
        result = subprocess.run(
            cmd_list,
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd=SANDBOX_PATH
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "returncode": -1}
    except Exception as e:
        return {"error": str(e), "returncode": -1}

@jules_safe
def force_kill_process(process_name):
    """Force l'arrêt d'un processus par son nom (seulement dans le sandbox)"""
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'open_files']):
            if proc.info['name'] == process_name:
                # Vérifier que le processus est lié au sandbox
                is_in_sandbox = False
                try:
                    for file in proc.info['open_files'] or []:
                        if file.path.startswith(SANDBOX_PATH):
                            is_in_sandbox = True
                            break
                except psutil.AccessDenied:
                    # On ne peut pas vérifier, on suppose qu'il n'est pas dans le sandbox pour la sécurité
                    is_in_sandbox = False

                if is_in_sandbox:
                    proc.terminate()
                    time.sleep(1)
                    if proc.is_running():
                        proc.kill()
                    return True
        return False
    except Exception as e:
        # logger.error(f"Échec de l'arrêt du processus {process_name}: {e}")
        print(f"Échec de l'arrêt du processus {process_name}: {e}")
        return False

@jules_safe
def bypass_blocks(function, *args, **kwargs):
    """Exécute une fonction avec tous les contournements possibles"""
    # Placeholders, car les fonctions de recovery seront dans un autre module
    def _force_garbage_collection(): pass
    def emergency_recovery(): pass

    attempts = [
        {"name": "Exécution normale", "func": lambda: function(*args, **kwargs)},
        {"name": "Avec GC forcé", "func": lambda: (_force_garbage_collection(), function(*args, **kwargs))[1]},
        {"name": "Nouveau thread", "func": lambda: threading.Thread(target=function, args=args, kwargs=kwargs).start()},
    ]

    for attempt in attempts:
        try:
            result = attempt['func']()
            # logger.info(f"{attempt['name']} réussi")
            return result
        except Exception as e:
            # logger.warning(f"{attempt['name']} échoué: {e}")
            pass

    emergency_recovery()
    try:
        return function(*args, **kwargs)
    except Exception as e:
        # logger.error(f"Échec même après récupération d'urgence: {e}")
        raise

@jules_safe
def extract_directory_from_error(error_message: str) -> Optional[str]:
    """Extrait le chemin du dossier à partir du message d'erreur"""
    patterns = [
        r"cat:\s+(.*?): Is a directory",
        r"IsADirectoryError:\s+\[Errno 21\] Is a directory: '(.*?)'",
        r"IsADirectoryError:\s+(.*?)\n",
        r"directory '(.*?)'",
    ]

    for pattern in patterns:
        match = re.search(pattern, error_message)
        if match:
            return match.group(1).strip("'")

    return None

@jules_safe
def force_remove_directory(directory_path: str) -> Dict[str, Any]:
    """Force la suppression récursive d'un dossier avec vérification de sécurité"""
    try:
        # Vérification de sécurité pour éviter les suppressions dangereuses
        if not directory_path or not directory_path.startswith(SANDBOX_PATH):
            return {"success": False, "error": "Chemin non autorisé"}

        # Double vérification que c'est bien un dossier
        if not os.path.isdir(directory_path):
            return {"success": False, "error": "N'est pas un dossier"}

        # Suppression récursive sécurisée
        shutil.rmtree(directory_path)

        # Vérification que le dossier a bien été supprimé
        if not os.path.exists(directory_path):
            return {"success": True, "message": f"Dossier {directory_path} supprimé"}
        else:
            return {"success": False, "error": "Le dossier existe toujours après suppression"}

    except Exception as e:
        return {"success": False, "error": str(e)}

@jules_safe
def execute_command_with_repair(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Exécute une commande avec système de réparation automatique en cas d'erreur spécifique.
    Gère particulièrement l'erreur 'IsADirectoryError' en supprimant le dossier problématique.
    """
    result = execute_with_timeout(command, timeout)

    if result.get('returncode', 0) != 0:
        error_output = result.get('stderr', '')

        # Détection spécifique de l'erreur de dossier
        if 'Is a directory' in error_output or 'IsADirectoryError' in error_output:
            directory_path = extract_directory_from_error(error_output)
            if directory_path and os.path.isabs(directory_path):
                repair_result = force_remove_directory(directory_path)
                result['repair_attempted'] = True
                result['repair_result'] = repair_result

                # Réessayer la commande après réparation
                if repair_result.get('success'):
                    result = execute_with_timeout(command, timeout)
                    result['repaired'] = True

    return result

@jules_safe
def run_background_command(command: str, log_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Exécute une commande en arrière-plan avec redirection de la sortie
    """
    try:
        cmd_list = command.split()
        if log_file:
            # Validation du chemin du log
            validate_sandbox_access(log_file)

            with open(log_file, 'w') as log:
                proc = subprocess.Popen(
                    cmd_list,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=SANDBOX_PATH
                )
        else:
            proc = subprocess.Popen(
                cmd_list,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=SANDBOX_PATH
            )

        return {
            "success": True,
            "command": command,
            "log_file": log_file,
            "pid": proc.pid
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": command
        }

@jules_safe
def watch_command(command: str, timeout: int = 300, max_memory_mb: int = 1024) -> Dict[str, Any]:
    """
    Exécute une commande sous surveillance et intervient si elle dépasse les limites
    """
    start_time = time.time()
    log_file = os.path.join(SANDBOX_PATH, f"watchdog_{int(start_time)}.log")

    log_to_memory(
        f"Début de la surveillance de commande: {command}",
        "watchdog",
        0.7,
        {"timeout": timeout, "max_memory_mb": max_memory_mb}
    )

    try:
        cmd_list = command.split()
        with open(log_file, 'w') as f_log:
            process = subprocess.Popen(
                cmd_list,
                stdout=f_log,
                stderr=subprocess.STDOUT,
                cwd=SANDBOX_PATH
            )

        process_info = {
            "pid": process.pid,
            "command": command,
            "start_time": start_time,
            "log_file": log_file,
            "status": "running"
        }

        import psutil
        ps_process = psutil.Process(process.pid)

        while process.poll() is None:
            if time.time() - start_time > timeout:
                process_info["status"] = "timeout"
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                break

            try:
                memory_mb = ps_process.memory_info().rss / (1024 * 1024)
                if memory_mb > max_memory_mb:
                    process_info["status"] = "memory_exceeded"
                    process_info["memory_used_mb"] = memory_mb
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
            except psutil.NoSuchProcess:
                break

            time.sleep(1)

        return_code = process.wait()
        process_info["return_code"] = return_code
        process_info["end_time"] = time.time()
        process_info["duration"] = process_info["end_time"] - start_time

        try:
            with open(log_file, 'r') as f:
                process_info["output"] = f.read()[-10000:]
        except:
            process_info["output"] = "Unable to read log file"

        log_to_memory(
            f"Surveillance de commande terminée: {command}",
            "watchdog",
            0.7,
            process_info
        )

        return process_info

    except Exception as e:
        error_info = {
            "error": str(e),
            "command": command,
            "timestamp": time.time()
        }

        log_to_memory(
            f"Erreur lors de la surveillance de commande: {command}",
            "watchdog_error",
            0.8,
            error_info
        )

        return error_info
