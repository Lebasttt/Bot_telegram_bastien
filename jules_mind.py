# ==============================================================================
# JULES - INTERFACE DE L'ESPRIT (jules_mind.py)
# ------------------------------------------------------------------------------
# Ce script est l'interface de pilotage de l'agent IA (Jules). Il est exécuté
# par l'agent lui-même pour interagir avec le corps de l'avatar. Il lit le
# statut du corps, affiche la mission à l'agent, prend en entrée la commande
# de l'agent, et la transmet au corps via le Gist.
# ==============================================================================

import os
import time
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
GIST_ID = os.getenv("GIST_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

JULES_COMMAND_FILE = "jules_command.txt"
AVATAR_STATUS_FILE = "avatar_status.txt"

# --- Fonctions de l'Interface ---

def log(message):
    print(f"{datetime.utcnow().isoformat() + 'Z'} - {message}")

def read_gist_file(file_name):
    api_url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        gist_data = response.json()
        return gist_data.get("files", {}).get(file_name, {}).get("content", "")
    except Exception as e:
        log(f"ERREUR GIST-RX: {e}")
        return None

def update_gist_file(file_name, content):
    log(f"GIST-TX: Écriture dans '{file_name}'...")
    api_url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {"files": {file_name: {"content": content}}}
    try:
        response = requests.patch(api_url, headers=headers, json=data)
        response.raise_for_status()
    except Exception as e:
        log(f"ERREUR GIST-TX: {e}")

# --- Boucle de Pilotage ---

def main_loop():
    log("--- INTERFACE DE L'ESPRIT ACTIVÉE ---")
    last_processed_status = ""

    while True:
        log("Vérification du statut de l'avatar...")
        status = read_gist_file(AVATAR_STATUS_FILE)

        if status and status != last_processed_status:
            log(f"NOUVEAU STATUT: {status}")

            if status.startswith("[REQUÊTE D'ÉVOLUTION]"):
                # Affiche la mission pour l'agent IA
                print("\n" + "="*50)
                print("NOUVELLE REQUÊTE D'ÉVOLUTION REÇUE")
                print(f"Statut du corps: {status}")
                print("="*50)

                # Demande à l'agent (l'humain ou l'IA qui exécute ce script) de fournir une commande
                # C'EST ICI QUE L'INTELLIGENCE DE L'AGENT INTERVIENT
                try:
                    command_input = input("Veuillez fournir la commande shell pour accomplir cette mission:\n> ")

                    if command_input:
                        # Envoie la commande au corps
                        update_gist_file(JULES_COMMAND_FILE, command_input)

                        # Attend la confirmation
                        log("Commande envoyée. En attente de la confirmation du corps...")
                        time.sleep(25) # Laisse le temps au corps de réagir

                        confirmation_status = read_gist_file(AVATAR_STATUS_FILE)
                        if confirmation_status and confirmation_status.startswith("[CONFIRMATION]"):
                            log("Confirmation reçue. Autorisation de l'exécution.")
                            update_gist_file(JULES_COMMAND_FILE, "EXECUTE")
                        else:
                            log("Le corps n'a pas confirmé. Annulation.")
                            update_gist_file(JULES_COMMAND_FILE, "CANCELLED")
                    else:
                        log("Aucune commande fournie. Annulation.")

                except EOFError:
                    log("Aucune entrée reçue. La session est peut-être non-interactive.")

            last_processed_status = status
        else:
            log("Aucun nouveau statut.")

        time.sleep(30)

if __name__ == "__main__":
    if not all([GIST_ID, GITHUB_TOKEN]):
        log("ERREUR: GIST_ID et GITHUB_TOKEN doivent être définis.")
    else:
        main_loop()
