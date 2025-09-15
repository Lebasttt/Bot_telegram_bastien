import json
from typing import Dict, Any

# --- Dépendances inter-modules ---
from ..core.config import CONFIG
from ..core.logging import logger
from ..core.security import jules_safe

@jules_safe
def send_telemetry(event_type: str, data: Dict[str, Any]):
    """
    Envoie des données de télémétrie si l'option est activée.

    NOTE: Ceci est une implémentation placeholder. Elle ne fait qu'afficher
    les données dans les logs au lieu de les envoyer sur un réseau.
    """
    telemetry_config = CONFIG.get("TELEMETRY", {})
    if not telemetry_config.get("ENABLE_TELEMETRY", False):
        return

    telemetry_payload = {
        "event": event_type,
        "data": data,
        "source": "jules_supervisor"
    }

    # Implémentation réelle :
    # try:
    #     import requests
    #     endpoint = telemetry_config.get("ENDPOINT_URL")
    #     if endpoint:
    #         response = requests.post(endpoint, json=telemetry_payload, timeout=10)
    #         response.raise_for_status()
    #         logger.debug("Télémétrie envoyée avec succès.")
    # except Exception as e:
    #     logger.warning(f"Échec de l'envoi de la télémétrie: {e}")

    # Implémentation placeholder :
    logger.info(f"[TELEMETRY] Event: {event_type}, Payload: {json.dumps(telemetry_payload)}")
