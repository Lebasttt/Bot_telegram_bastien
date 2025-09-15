import os
import subprocess
import json
import time
from typing import Dict, List, Any

# --- Dépendances inter-modules ---
from ..core.config import CONFIG
from ..core.logging import logger
from ..core.memory import log_to_memory
from ..core.security import jules_safe

@jules_safe
def detect_project_type() -> List[str]:
    """Détermine le type de projet (python, node, etc.) en cherchant des fichiers spécifiques."""
    project_types = set()
    sandbox_path = CONFIG.get("SANDBOX_PATH", ".")

    project_files = {
        "python": ["requirements.txt", "pyproject.toml", "setup.py"],
        "node": ["package.json"],
        "go": ["go.mod"],
        "ruby": ["Gemfile"],
        "php": ["composer.json"],
    }

    for p_type, files in project_files.items():
        for file in files:
            if os.path.exists(os.path.join(sandbox_path, file)):
                project_types.add(p_type)
                break

    return list(project_types)

@jules_safe
def audit_python_dependencies(results: Dict[str, Any]):
    """Exécute un audit sur les dépendances Python avec pip-audit ou safety."""
    sandbox_path = CONFIG.get("SANDBOX_PATH", ".")

    # Tenter avec pip-audit
    try:
        # Utiliser `pip-audit --json` pour une sortie structurée
        audit_cmd = ["pip-audit", "--json"]
        proc = subprocess.run(
            audit_cmd, capture_output=True, text=True, cwd=sandbox_path, timeout=180, check=False
        )
        results["tools_used"].append("pip-audit")

        if proc.stdout:
            try:
                audit_data = json.loads(proc.stdout)
                for vuln in audit_data.get("vulnerabilities", []):
                    results["vulnerabilities"].append({
                        "package": vuln.get("name"),
                        "version": vuln.get("version"),
                        "vulnerability_id": vuln.get("id"),
                        "description": vuln.get("description"),
                        "fix_versions": vuln.get("fix_versions"),
                        "tool": "pip-audit"
                    })
                return # Succès avec pip-audit, on s'arrête là
            except json.JSONDecodeError:
                results["errors"].append("pip-audit: Failed to parse JSON output.")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        results["errors"].append(f"pip-audit failed: {e}")

    # Fallback sur safety si pip-audit n'est pas disponible ou a échoué
    try:
        safety_cmd = ["safety", "check", "--json"]
        proc = subprocess.run(
            safety_cmd, capture_output=True, text=True, cwd=sandbox_path, timeout=180, check=False
        )
        results["tools_used"].append("safety")
        if proc.stdout:
            try:
                # La sortie de safety est une liste de vulnérabilités
                safety_data = json.loads(proc.stdout)
                for vuln in safety_data:
                     results["vulnerabilities"].append({
                        "package": vuln[0], # package name
                        "affected_versions": vuln[2],
                        "installed_version": vuln[1],
                        "vulnerability_id": vuln[3],
                        "description": "N/A",
                        "tool": "safety"
                    })
            except json.JSONDecodeError:
                 results["errors"].append("safety: Failed to parse JSON output.")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        results["errors"].append(f"safety failed: {e}")


@jules_safe
def audit_node_dependencies(results: Dict[str, Any]):
    """Exécute `npm audit` sur un projet Node.js."""
    sandbox_path = CONFIG.get("SANDBOX_PATH", ".")
    try:
        npm_cmd = ["npm", "audit", "--json"]
        proc = subprocess.run(
            npm_cmd, capture_output=True, text=True, cwd=sandbox_path, timeout=300, check=False
        )
        results["tools_used"].append("npm-audit")

        # npm audit peut retourner un code > 0 même en cas de succès (si des vulnérabilités sont trouvées)
        if proc.stdout:
            try:
                audit_data = json.loads(proc.stdout)
                for name, vuln_info in audit_data.get("vulnerabilities", {}).items():
                    results["vulnerabilities"].append({
                        "package": name,
                        "severity": vuln_info.get("severity"),
                        "is_direct": vuln_info.get("isDirect"),
                        "via": [v.get("title", v) if isinstance(v, dict) else v for v in vuln_info.get("via", [])],
                        "fix_available": vuln_info.get("fixAvailable"),
                        "tool": "npm-audit"
                    })
            except json.JSONDecodeError:
                results["errors"].append("npm-audit: Failed to parse JSON output.")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        results["errors"].append(f"npm-audit failed: {e}")

@jules_safe
def check_dependencies() -> Dict[str, Any]:
    """Orchestre l'audit de sécurité des dépendances du projet."""
    results: Dict[str, Any] = {
        "timestamp": time.time(),
        "project_type": detect_project_type(),
        "vulnerabilities": [],
        "tools_used": [],
        "errors": []
    }

    if not results["project_type"]:
        logger.info("Aucun type de projet de dépendance connu détecté.")
        return results

    if "python" in results["project_type"]:
        audit_python_dependencies(results)

    if "node" in results["project_type"]:
        audit_node_dependencies(results)

    # Sauvegarder le rapport
    report_file = CONFIG.get("DEPENDENCY_AUDIT_FILE")
    if report_file:
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur de sauvegarde du rapport d'audit de dépendances: {e}")
            results["errors"].append(f"Failed to save report: {e}")

    # Loguer dans la mémoire
    vuln_count = len(results["vulnerabilities"])
    log_to_memory(
        f"Audit de dépendances terminé: {vuln_count} vulnérabilités trouvées.",
        "security",
        0.9,
        {"project_type": results["project_type"], "vulnerabilities_found": vuln_count}
    )

    return results
