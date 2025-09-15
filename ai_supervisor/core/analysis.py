import json
import os
import time
from typing import Any, Dict, List, Optional

# These will be resolved once the files are created
from .config import CONFIG
from .logging import logger
from .memory import get_recent_memory_activities
from .security import jules_safe

LOG_FILE = CONFIG.get("LOG_FILE")
SANDBOX_PATH = CONFIG.get("SANDBOX_PATH", ".")
ANALYSIS_FILE = os.path.join(SANDBOX_PATH, "root_cause_analysis.json")

@jules_safe
def analyze_temporal_patterns() -> Dict[str, Any]:
    """Analyse les patterns temporels dans les erreurs à partir du fichier de log."""
    if not LOG_FILE or not os.path.exists(LOG_FILE):
        return {'error': 'Log file not found or not configured.'}

    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Parser seulement les lignes JSON valides
        logs = []
        for line in lines:
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        error_events = ['unhandled_exception', 'system_health_poor', 'tracer_error', 'auto_recovery_triggered']
        error_logs = [log for log in logs if log.get('event') in error_events]

        if len(error_logs) < 2:
            return {
                'total_errors': len(error_logs),
                'analysis': 'Not enough data for temporal analysis.'
            }

        error_times = sorted([log.get('time', 0) for log in error_logs])
        time_diffs = [error_times[i] - error_times[i-1] for i in range(1, len(error_times))]

        avg_time_between_errors = sum(time_diffs) / len(time_diffs) if time_diffs else 0

        frequency = 'occasional'
        if avg_time_between_errors < 60:
            frequency = 'very_frequent'
        elif avg_time_between_errors < 300:
            frequency = 'frequent'

        return {
            'total_errors': len(error_logs),
            'avg_time_between_errors_sec': avg_time_between_errors,
            'error_frequency': frequency,
            'first_error_time': error_times[0],
            'last_error_time': error_times[-1]
        }

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des patterns temporels: {e}")
        return {'error': f'Temporal analysis failed: {e}'}

@jules_safe
def analyze_root_cause(error_info: Dict, recent_activities: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Tente d'identifier la cause racine d'une erreur en analysant le contexte.
    """
    if recent_activities is None:
        recent_activities = get_recent_memory_activities(20)

    analysis = {
        "timestamp": time.time(),
        "error_info": error_info,
        "hypotheses": [],
        "confidence": 0.0,
        "related_activities": [],
        "summary": "Aucune hypothèse forte identifiée."
    }

    error_message = str(error_info.get("message", "")).lower()
    stack_trace_str = json.dumps(error_info.get("stack_trace", [])).lower()
    full_error_text = error_message + ' ' + stack_trace_str

    # Patterns de problèmes courants
    patterns = {
        "dependency_issue": ["modulenotfounderror", "importerror", "npm err", "pip error", "package not found", "cannot find module", "require is not defined"],
        "memory_issue": ["memoryerror", "out of memory", "heap out", "allocation failed", "killed", "signal 9"],
        "permission_issue": ["permission denied", "eacces", "access denied", "read-only", "operation not permitted"],
        "filesystem_issue": ["no such file or directory", "enoent", "file already exists", "is a directory", "not a directory", "disk full"],
        "timeout_issue": ["timeout", "timed out", "operation exceeded", "tle", "timeout expired"],
        "network_issue": ["connection refused", "econnreset", "dns lookup failed", "network is unreachable"],
        "type_error": ["typeerror", "must be str, not int", "unsupported operand type"],
        "key_error": ["keyerror"],
    }

    # Générer des hypothèses basées sur les patterns
    for category, indicators in patterns.items():
        for indicator in indicators:
            if indicator in full_error_text:
                analysis["hypotheses"].append({
                    "category": category,
                    "indicator": indicator,
                    "confidence": 0.6
                })

    # Analyser la stack trace pour des activités récentes liées
    for frame in error_info.get("stack_trace", []):
        filename = frame.get("filename", "")
        for activity in recent_activities:
            activity_str = json.dumps(activity).lower()
            if filename and filename in activity_str:
                analysis["related_activities"].append(activity)
                # Augmenter la confiance si une activité est directement liée
                for hypo in analysis["hypotheses"]:
                    hypo["confidence"] = min(1.0, hypo["confidence"] + 0.1)

    # Calculer la confiance globale et le résumé
    if analysis["hypotheses"]:
        # Trier par confiance pour avoir la meilleure hypothèse en premier
        analysis["hypotheses"].sort(key=lambda x: x["confidence"], reverse=True)
        best_hypothesis = analysis["hypotheses"][0]
        analysis["confidence"] = best_hypothesis["confidence"]
        analysis["summary"] = f"Hypothèse principale: {best_hypothesis['category']} (indicateur: '{best_hypothesis['indicator']}', confiance: {analysis['confidence']:.2f})."
        if analysis["related_activities"]:
            analysis["summary"] += f" {len(analysis['related_activities'])} activités récentes pourraient être liées."

    # Sauvegarder l'analyse
    try:
        analyses = []
        if os.path.exists(ANALYSIS_FILE):
            with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    analyses = json.loads(content)

        if not isinstance(analyses, list):
            analyses = []

        analyses.append(analysis)

        with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
            # Utiliser un default=str pour gérer les types non sérialisables
            json.dump(analyses, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Erreur de sauvegarde de l'analyse de cause racine: {e}")

    return analysis
