import sys
import inspect
import pdb
import io
import time
import functools
from typing import Any, Callable, Dict, List, Optional, Set, FrameType

# --- Dépendances inter-modules ---
from .logging import emit
from .security import jules_safe
from ..utils.helpers import _hash_obj, safe_repr

# --- Variables globales pour le tracing ---
TRACE_LOG: List[Dict] = []
TRACE_FILTERS: List[Callable[[FrameType, str, Any], bool]] = []

# --- Introspection d'objets ---

@jules_safe
def introspect(obj: Any, depth: int = 2, _seen: Optional[Set[int]] = None, _path: str = "") -> Dict[str, Any]:
    """Introspection récursive et sécurisée d'un objet."""
    if _seen is None:
        _seen = set()

    obj_id = id(obj)
    if obj_id in _seen:
        return {"type": "circular_reference", "id": obj_id}
    _seen.add(obj_id)

    result: Dict[str, Any] = {
        "type": type(obj).__name__,
        "id": obj_id,
        "hash": _hash_obj(obj),
    }

    try:
        if depth <= 0:
            result["value"] = safe_repr(obj, 150)
        elif isinstance(obj, (int, float, str, bool, type(None))):
            result["value"] = obj
        elif isinstance(obj, (list, tuple, set)):
            result["length"] = len(obj)
            if depth > 0 and len(obj) < 20:
                result["items"] = [introspect(item, depth - 1, _seen, f"{_path}[{i}]") for i, item in enumerate(obj)]
        elif isinstance(obj, dict):
            result["length"] = len(obj)
            if depth > 0 and len(obj) < 20:
                result["items"] = {str(k): introspect(v, depth - 1, _seen, f"{_path}[{k}]") for k, v in obj.items()}
        else:
            result["value"] = safe_repr(obj, 200)
    except Exception as e:
        result["error"] = f"Introspection error: {e}"

    _seen.remove(obj_id)
    return result

# --- Tracing d'exécution ---

def ultra_tracer(frame: FrameType, event: str, arg: Any) -> Optional[Callable]:
    """Tracer global qui enregistre les appels de fonction, les retours, etc."""
    try:
        # Appliquer les filtres pour ignorer certains appels
        for filter_func in TRACE_FILTERS:
            if not filter_func(frame, event, arg):
                return ultra_tracer

        trace_info = {
            "event": event,
            "filename": frame.f_code.co_filename,
            "function": frame.f_code.co_name,
            "line": frame.f_lineno,
            "time": time.time(),
            "arg": safe_repr(arg, 100) if arg else None
        }
        TRACE_LOG.append(trace_info)

        # Émettre des événements pour un suivi en temps réel plus facile
        if event in ["call", "return"]:
            emit(f"trace_{event}", {
                "function": frame.f_code.co_name,
                "filename": frame.f_code.co_filename,
                "line": frame.f_lineno
            })
    except Exception:
        # Ignorer les erreurs dans le tracer pour ne pas perturber l'exécution
        pass

    return ultra_tracer

def enable_global_trace(filters: Optional[List[Callable]] = None):
    """Active le tracing global."""
    global TRACE_FILTERS
    if filters:
        TRACE_FILTERS = filters
    sys.settrace(ultra_tracer)

def disable_global_trace() -> List[Dict]:
    """Désactive le tracing et retourne le journal accumulé."""
    sys.settrace(None)
    log = TRACE_LOG.copy()
    TRACE_LOG.clear()
    return log

# --- Décorateurs pour le tracing et le timing ---

def trace_and_time(enabled: bool = True):
    """Décorateur pour tracer l'entrée, la sortie, et le temps d'exécution d'une fonction."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not enabled:
                return func(*args, **kwargs)

            start_time = time.time()
            emit("function_entry", {
                "func": func.__name__,
                "args": safe_repr(args, 400),
                "kwargs": safe_repr(kwargs, 400),
            })

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                emit("function_exit", {
                    "func": func.__name__,
                    "execution_time_sec": execution_time,
                    "result": safe_repr(result, 400)
                })
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                emit("function_exception", {
                    "func": func.__name__,
                    "execution_time_sec": execution_time,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                })
                raise
        return wrapper
    return decorator

# --- Débogueur non interactif ---

class RobustNonInteractivePdb(pdb.Pdb):
    """Version de PDB conçue pour l'analyse automatique et non interactive."""
    def __init__(self, *args, **kwargs):
        self.stdout_capture = io.StringIO()
        # PDB attend un file-like object, pas un TextIOWrapper
        kwargs["stdout"] = self.stdout_capture
        super().__init__(*args, **kwargs)
        self.frame_analysis = []
        self.auto_continue = True # Forcer la continuation automatique

    def do_continue(self, arg):
        # S'assurer que le script ne reste pas bloqué
        self.clear_all_breaks()
        return super().do_continue(arg)

    def interaction(self, frame, traceback):
        # Analyser l'état et continuer au lieu d'attendre une entrée
        self.analyze_current_frame(frame)
        if self.auto_continue:
            self.set_continue()

    def analyze_current_frame(self, frame):
        """Analyse le frame courant et stocke les informations."""
        try:
            analysis = {
                "filename": frame.f_code.co_filename,
                "function": frame.f_code.co_name,
                "line": frame.f_lineno,
                "locals": introspect(frame.f_locals, depth=1),
            }
            self.frame_analysis.append(analysis)
        except Exception as e:
            self.frame_analysis.append({"error": f"Frame analysis failed: {e}"})

    def get_analysis(self) -> List[Dict]:
        """Retourne les analyses de frames collectées."""
        return self.frame_analysis
