import os
import re
import subprocess
import json
import time
from typing import Dict, List, Optional, Any

# --- Dépendances inter-modules ---
from ..core.config import CONFIG
from ..core.logging import logger
from ..core.memory import log_to_memory
from ..core.security import jules_safe

def is_false_positive(secret_match: Dict[str, Any]) -> bool:
    """
    Détecte les faux positifs courants dans les résultats de scan de secrets
    en se basant sur des mots-clés comme 'example', 'test', 'mock'.
    """
    # Patterns de faux positifs
    false_positive_patterns = [
        r'example[_-]?(key|token|secret)',
        r'test[_-]?(api|key|token)',
        r'placeholder',
        r'changeme',
        r'xxxxx',
        r'mock[_-]',
        r'dummy',
        r'fake',
    ]

    # Concaténer le match et le contexte pour une recherche globale
    text_to_check = str(secret_match.get('match', '')) + " " + str(secret_match.get('context', ''))
    text_to_check = text_to_check.lower()

    for pattern in false_positive_patterns:
        if re.search(pattern, text_to_check):
            return True

    # Ignorer les UUIDs qui sont rarement des secrets
    if re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', str(secret_match.get('match', ''))):
        return True

    return False

@jules_safe
def scan_for_secrets(file_paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Analyse les fichiers spécifiés ou les fichiers modifiés (git) pour détecter des secrets.
    """
    results: Dict[str, Any] = {
        "secrets_found": [],
        "files_scanned": 0,
        "patterns_matched": 0,
        "timestamp": time.time(),
        "errors": []
    }

    patterns = [re.compile(p) for p in CONFIG.get("SECRET_SCAN_PATTERNS", [])]
    sandbox_path = CONFIG.get("SANDBOX_PATH", ".")

    # Si aucun chemin n'est fourni, tenter de trouver les fichiers modifiés via git
    if file_paths is None:
        try:
            # --no-pager pour éviter les problèmes dans les environnements non interactifs
            git_diff = subprocess.run(
                ["git", "--no-pager", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                capture_output=True, text=True, cwd=sandbox_path, check=False
            )
            if git_diff.returncode == 0 and git_diff.stdout:
                file_paths = [os.path.join(sandbox_path, f) for f in git_diff.stdout.strip().split('\n')]
            else:
                # Fallback : scanner tous les fichiers pertinents si git diff échoue ou est vide
                file_paths = []
                for root, _, files in os.walk(sandbox_path):
                    for file in files:
                        if file.endswith(('.py', '.js', '.json', '.yml', '.yaml', '.env', '.sh')):
                            file_paths.append(os.path.join(root, file))
        except Exception as e:
            logger.error(f"Erreur lors de la détection des fichiers modifiés via git: {e}")
            results["errors"].append(f"Git diff failed: {e}")
            file_paths = [] # Assurer que file_paths est une liste

    # Scanner chaque fichier
    for file_path in file_paths:
        if not os.path.isfile(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Lire ligne par ligne pour la performance et la gestion de la mémoire
                for line_num, line in enumerate(f, 1):
                    for pattern in patterns:
                        for match in pattern.finditer(line):
                            secret_details = {
                                "file": os.path.relpath(file_path, sandbox_path),
                                "line": line_num,
                                "pattern": pattern.pattern,
                                "match": match.group(0),
                                "context": line.strip()
                            }
                            if not is_false_positive(secret_details):
                                results["secrets_found"].append(secret_details)
                                results["patterns_matched"] += 1
            results["files_scanned"] += 1
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du fichier {file_path}: {e}")
            results["errors"].append(f"Error scanning {file_path}: {e}")

    # Sauvegarder le rapport
    report_file = CONFIG.get("SECRETS_SCAN_FILE")
    if report_file:
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur de sauvegarde du rapport de secrets: {e}")
            results["errors"].append(f"Failed to save report: {e}")

    # Loguer dans la mémoire
    log_to_memory(
        f"Scan de sécurité terminé: {results['patterns_matched']} secrets potentiels trouvés.",
        "security",
        0.8,
        {"files_scanned": results["files_scanned"], "secrets_found": len(results["secrets_found"])}
    )

    return results
