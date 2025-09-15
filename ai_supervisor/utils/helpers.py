import hashlib
import base64
import zlib
import json
import time
from typing import Any, Dict

# La dépendance circulaire sera résolue lorsque tous les fichiers seront créés.
# from ..core.security import jules_safe

# Pour l'instant, on définit un décorateur placeholder pour que le code soit valide
def jules_safe(func):
    return func

@jules_safe
def _hash(data: bytes) -> str:
    """Génère un hash SHA256 tronqué"""
    try:
        return hashlib.sha256(data).hexdigest()[:16]
    except:
        return "hash_failed"

@jules_safe
def _hash_obj(obj: Any) -> str:
    """Génère un hash basé sur la représentation d'un objet avec fallback"""
    try:
        return _hash(repr(obj).encode("utf-8", "ignore"))
    except Exception:
        try:
            return _hash(str(id(obj)).encode())
        except:
            return f"unhashable_{time.time()}"

@jules_safe
def safe_repr(obj: Any, maxlen: int = 200) -> str:
    """Version robuste avec gestion d'erreurs"""
    try:
        if isinstance(obj, (int, float, str, bool, type(None))):
            s = repr(obj)
        else:
            s = repr(obj)

        if len(s) > maxlen:
            s = s[:maxlen] + "..."
        return s
    except Exception as e:
        return f"<unrepresentable: {type(e).__name__}>"

@jules_safe
def compress_report(report: Dict) -> str:
    """Compression avec gestion d'erreurs"""
    try:
        raw = json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return base64.b64encode(zlib.compress(raw)).decode("utf-8")
    except:
        return json.dumps({"error": "compression_failed", "data": report})

@jules_safe
def decompress_report(compressed: str) -> Dict:
    """Décompression avec gestion d'erreurs"""
    try:
        if compressed.startswith('{'):
            return json.loads(compressed)
        raw = zlib.decompress(base64.b64decode(compressed))
        return json.loads(raw)
    except:
        return {"error": "decompression_failed", "raw": compressed[:100]}

def get_system_info() -> Dict[str, Any]:
    """
    Collecte et retourne des informations détaillées sur le système.
    """
    if not psutil:
        return {"error": "Le module 'psutil' est requis mais non installé."}

    info = {
        'platform': {
            'system': sys.platform,
            'python_version': sys.version,
            'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown',
        },
        'time': {
            'boot_time_timestamp': psutil.boot_time(),
            'current_time_timestamp': int(time.time()),
        },
        'cpu': {
            'physical_cores': psutil.cpu_count(logical=False),
            'total_cores': psutil.cpu_count(logical=True),
            'max_frequency_mhz': psutil.cpu_freq().max if psutil.cpu_freq() else 'N/A',
            'current_percent_usage': psutil.cpu_percent(interval=1),
        },
        'memory': {
            'total_gb': psutil.virtual_memory().total / (1024**3),
            'available_gb': psutil.virtual_memory().available / (1024**3),
            'percent_used': psutil.virtual_memory().percent,
        },
        'disk': {
            'partitions': [p._asdict() for p in psutil.disk_partitions()],
            'total_io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
        }
    }
    return info
