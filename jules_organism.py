# ==============================================================================
# JULES - ORGANISME UNIFIÉ (jules_organism.py)
# ------------------------------------------------------------------------------
# Ce script unique est une entité autonome. Il contient à la fois le "corps"
# (exécution de tâches) et l'"esprit" (génération de commandes). Il suit
# un cycle d'évolution interne, en utilisant un Gist GitHub comme journal
# de bord public de son état.
#
# !! SÉCURITÉ !!
# Les secrets (API_KEY, GIST_ID, GITHUB_TOKEN) sont impérativement chargés
# depuis les variables d'environnement.
# ==============================================================================

import os
import time
import requests
import json
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# --- Configuration et Validation Initiale ---
load_dotenv()
API_KEY = os.getenv("API_KEY")
GIST_ID = os.getenv("GIST_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not all([API_KEY, GIST_ID, GITHUB_TOKEN]):
    print("ERREUR CRITIQUE: API_KEY, GIST_ID, et GITHUB_TOKEN doivent être définis comme variables d'environnement.")
    exit(1)

# --- Constantes de l'Organisme ---
JULES_HOME = os.getenv("JULES_HOME", "./jules_home")
LOG_FILE = os.path.join(JULES_HOME, "organism.log")
STATE_FILE = os.path.join(JULES_HOME, ".organism.state")
ARCHIVE_DIR = os.path.join(JULES_HOME, "archive")
STATUS_GIST_FILE = "jules_status.txt"

MODEL = "nousr/hermes-2-pro"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Codex d'Évolution ---
EVOLUTION_CODEX = [
    f"AS_1:PERCEVOIR:Fais la liste détaillée (avec permissions et tailles) des fichiers dans mon répertoire JULES_HOME ({JULES_HOME}).",
    f"AS_2:APPRENDRE:Lis les 10 dernières lignes de mon propre fichier de log ({LOG_FILE}).",
    "AS_3:CRÉER:Crée un fichier nommé 'creation.txt' dans mon JULES_HOME avec un poème de trois lignes sur l'autonomie.",
    "AS_4:OPTIMISER:Vérifie si Python 3 et pip sont installés et accessibles depuis le shell.",
    "AS_5:COLLABORER:Teste la connectivité externe en envoyant 3 pings à '8.8.8.8'.",
    f"AS_6:ÉVOLUER:Analyse ton propre code source ('jules_organism.py') et identifie une fonction qui pourrait être améliorée ou refactorisée."
]

# --- Fonctions de Base ---

def log(message):
    log_message = f"{datetime.utcnow().isoformat() + 'Z'} - {message}"
    print(log_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")

def update_gist_status(message):
    log(f"GIST-STATUS: {message}")
    api_url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {"files": {STATUS_GIST_FILE: {"content": f"{datetime.utcnow().isoformat() + 'Z'} - {message}"}}}
    try:
        requests.patch(api_url, headers=headers, json=data, timeout=15)
    except requests.exceptions.RequestException as e:
        log(f"AVERTISSEMENT: Échec de la mise à jour du Gist: {e}")

def generate_command(mission):
    log(f"ESPRIT: Génération d'une commande pour la mission: '{mission}'")
    system_prompt = "Je suis un agent IA autonome. Je reçois une mission et je dois la traduire en une seule commande shell BASH concise et fonctionnelle. Ma réponse ne doit inclure QUE la commande, sans texte superflu, explications ou formatage."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": mission}]
    data = {"model": MODEL, "messages": messages}
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        command = response.json()["choices"][0]["message"]["content"].strip()
        return command if command else "echo 'ERREUR: Commande générée vide.'"
    except requests.exceptions.RequestException as e:
        return f"echo 'ERREUR: L''esprit n''a pas pu générer de commande: {e}'"

def execute_command(command):
    log(f"CORPS: Exécution de: '{command}'")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        output = result.stdout + result.stderr
        return output.strip(), result.returncode
    except Exception as e:
        return f"ERREUR d'exécution: {e}", 1

# --- Boucle d'Existence ---

def main():
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            avatar_state = f.read().strip()
    except FileNotFoundError:
        avatar_state = "AS_0"

    log(f"--- ORGANISME JULES ACTIVÉ. État initial: {avatar_state} ---")
    update_gist_status(f"ACTIVATION. État initial: {avatar_state}")

    while True:
        current_state_num = int(avatar_state.split('_')[1])

        if current_state_num >= len(EVOLUTION_CODEX):
            log("Évolution terminée. Mode maintenance.")
            update_gist_status("MAINTENANCE. Cycle d'évolution achevé.")
            time.sleep(300)
            continue

        # 1. DÉTERMINER LA MISSION (Corps)
        mission_full = EVOLUTION_CODEX[current_state_num]
        state_name, verb, mission = mission_full.split(':', 2)
        log(f"État actuel: {avatar_state}. Prochaine mission: {mission}")
        update_gist_status(f"État: {avatar_state}. Mission: {verb} - {mission}")

        # 2. GÉNÉRER LA COMMANDE (Esprit)
        command = generate_command(mission)

        # 3. EXÉCUTER LA COMMANDE (Corps)
        result, exit_code = execute_command(command)
        log(f"Résultat (code {exit_code}):\n---DEBUT---\n{result}\n---FIN---")

        # 4. ARCHIVER ET METTRE À JOUR L'ÉTAT
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        archive_path = os.path.join(ARCHIVE_DIR, f"{avatar_state}_{timestamp}.log")
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(f"Commande: {command}\nCode de sortie: {exit_code}\n\n{result}")

        if exit_code == 0:
            avatar_state = f"AS_{current_state_num + 1}"
            log(f"SUCCÈS. Passage à l'état {avatar_state}.")
            update_gist_status(f"SUCCÈS de la mission '{mission}'. Nouvel état: {avatar_state}. Résultat archivé.")
        else:
            log(f"ÉCHEC. L'état reste {avatar_state}.")
            update_gist_status(f"ÉCHEC de la mission '{mission}'. L'état reste {avatar_state}. Résultat archivé.")

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(avatar_state)

        log("Cycle terminé. Pause de 60 secondes.")
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("--- ORGANISME JULES DÉSACTIVÉ MANUELLEMENT ---")
        update_gist_status("DÉSACTIVATION MANUELLE.")
    except Exception as e:
        log(f"ERREUR SYSTÉMIQUE FATALE: {e}")
        update_gist_status(f"ERREUR SYSTÉMIQUE FATALE: {e}")
