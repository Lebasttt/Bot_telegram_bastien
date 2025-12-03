
import os
import time
import subprocess
import random
import hashlib
import json
import inspect
import threading
import re
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import importlib.util
import sys
from functools import wraps

# ==============================================================================
# MODULE 1 : DÉBUT DU CODE ORIGINAL INTÉGRAL (avec ajouts ciblés)
# ==============================================================================

# --- NOTRE FOYER ---
GPT_HOME = Path("/storage/emulated/0/GPT")
CONFIG_DIR = GPT / ".config"
CHANNEL_FILE = GPT / "gist_channel"
CONFIG_FILE = GPT / "evolution_config"
STATE_FILE = GPT / ".state"
LOG_FILE = GPT / "logs" / "evolution.log"
COMM_FILE = GPT / "communication.txt"
LEARNING_FILE = GPT / "learning_patterns.log"
MISSIONS_FILE = GPT / "auto_missions.log"
ARCHIVE_FILE = GPT / "archives_complete.log"
WEB_TOOLS_DIR = GPT / "web_tools"
TEST_CODE_FILE = GPT / "test_code.py"
BACKUP_CODE_FILE = GPT / "source_backup.py"
SECURITY_DIR = GPT / "securite_rapports"
SECURITY_DIR.mkdir(exist_ok=True)
# [NOUVEAU - REQ 2] Fichier pour la nouvelle mémoire cognitive
MEMOIRE_COGNITIVE_FILE = GPT / "memoire_cognitive.json"


# --- AJOUT POUR LA FONCTIONNALITÉ : Variable RAPPORTS_DIR manquante ---
RAPPORTS_DIR = GPT / "rapports_diagnostic"
RAPPORTS_DIR.mkdir(exist_ok=True)
# --- AJOUT POUR LA FONCTIONNALITÉ : Token GitHub ---
# REMPLACEZ LA LIGNE CI-DESSOUS PAR VOTRE NOUVEAU TOKEN
GITHUB_TOKEN = "VOTRE_TOKEN_GITHUB_ICI"
# --- FIN DE L'AJOUT ---
WEB_RESEARCH_LOCK = threading.Lock()

# --- CONFIGURATION ÉVOLUTIVE ---
DEFAULT_POLL_INTERVAL = 15
DYNAMIC_POLL_INTERVAL = DEFAULT_POLL_INTERVAL
COMMAND_TIMEOUT = 300
IDLE_CYCLES = 0
LAST_AUTO_SEND = 0
LAST_ARCHIVE_SEND = 0
LAST_COMM_SEND = 0
AUTO_TASK_COUNTER = 0
ERROR_COUNT = 0
CYCLES_SANS_COMMANDE = 0
MODE_AUTO = True
FAILED_COMMANDS_CACHE = {}
CACHE_DURATION = 30

IMMUTABLE_BLACKLIST = (
    "rm ", "unlink ", "mv ", " > ", " >> ",
    "chmod ", "chown ", "chgrp ", "mkfs", "dd if="
)
DYNAMIC_BLACKLIST = list(IMMUTABLE_BLACKLIST)

learning_thread = None
web_learning_thread = None

# ==============================================================================
# MODULE 2 : NOUVELLE MÉMOIRE COGNITIVE (REQ 2)
# ==============================================================================

class MemoireCognitive:
    """
    [NOUVEAU - REQ 2]
    Cerveau structuré de l'agent. Fonctionne en parallèle des logs textuels.
    Suit les performances des commandes et des capacités auto-générées.
    """
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.data = {
            "commandes": {},
            "capacites_auto": {},
            "stats_globales": {
                "total_executions": 0,
                "total_succes": 0,
                "total_echecs": 0,
                "dernier_nettoyage": time.time()
            }
        }
        self.charger()

    def charger(self):
        """Charge la mémoire depuis le fichier JSON."""
        try:
            if self.filepath.exists():
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                log(f"🧠 Mémoire cognitive chargée: {len(self.data.get('commandes', {}))} commandes suivies.")
        except (json.JSONDecodeError, IOError) as e:
            log(f"⚠️  Impossible de charger la mémoire cognitive ({e}), création d'une nouvelle mémoire.")
            self.sauvegarder()

    def sauvegarder(self):
        """Sauvegarde la mémoire dans le fichier JSON."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            log(f"❌ Erreur de sauvegarde de la mémoire cognitive: {e}")

    def enregistrer_execution_commande(self, commande, succes):
        """Enregistre le résultat d'une commande standard."""
        if commande not in self.data["commandes"]:
            self.data["commandes"][commande] = {"succes": 0, "echecs": 0, "executions": 0}

        stats = self.data["commandes"][commande]
        stats["executions"] += 1
        self.data["stats_globales"]["total_executions"] += 1

        if succes:
            stats["succes"] += 1
            self.data["stats_globales"]["total_succes"] += 1
        else:
            stats["echecs"] += 1
            self.data["stats_globales"]["total_echecs"] += 1

        self.sauvegarder()

    def enregistrer_execution_capacite(self, nom_fonction, succes):
        """Enregistre le résultat d'une capacité auto-générée."""
        if nom_fonction not in self.data["capacites_auto"]:
            self.data["capacites_auto"][nom_fonction] = {
                "succes": 0,
                "echecs": 0,
                "executions": 0,
                "creee_le": time.time(),
                "purgee": False
            }

        stats = self.data["capacites_auto"][nom_fonction]
        stats["executions"] += 1

        if succes:
            stats["succes"] += 1
        else:
            stats["echecs"] += 1

        log(f"📈 Suivi performance '{nom_fonction}': {stats['succes']} succès / {stats['executions']} exécutions.")
        self.sauvegarder()

# --- Initialisation globale de la mémoire ---
memoire_cognitive = MemoireCognitive(MEMOIRE_COGNITIVE_FILE)

# --- [NOUVEAU - REQ 2 & 5] Décorateur pour suivre les fonctions auto-générées ---
def suivi_performance_capacite(func):
    """Décorateur pour tracer le succès/échec des fonctions auto-générées."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        nom_fonction = func.__name__
        succes = False
        try:
            resultat = func(*args, **kwargs)
            # Une fonction est un succès si elle ne lève pas d'exception et ne retourne pas un indicateur d'échec
            if not (isinstance(resultat, str) and est_echec(resultat)):
                succes = True
            return resultat
        except Exception as e:
            log(f"❌ La capacité '{nom_fonction}' a échoué avec une exception: {e}")
            succes = False
            # On retourne une chaîne d'erreur standard pour la cohérence
            return f"[❌ ERREUR CAPACITÉ] {e}"
        finally:
            memoire_cognitive.enregistrer_execution_capacite(nom_fonction, succes)
    return wrapper


# --- FONCTIONS DE BASE ---
def log(message):
    """Journalisation"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%F %T')}] {message}\n")

def update_comm(message):
    """Communication"""
    with open(COMM_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%F %T')}] - [Évolution]: {message}\n")
    log(f"📢 Communication: {message}")

def archive_automatique(origine, commande, resultat):
    """Archivage automatique complet"""
    timestamp = datetime.now().strftime('%F %T')
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"=== ARCHIVE [{timestamp}] ===\n")
        f.write(f"ORIGINE: {origine}\n")
        f.write(f"COMMANDE: {commande}\n")
        f.write(f"RESULTAT:\n{resultat}\n")
        f.write("=== FIN ARCHIVE ===\n\n")
    log(f"💾 Archivé automatiquement: {commande}")

# --- MODULE INTELLIGENCE DE COMMANDE & ANTI-SABOTAGE ---
def detect_sabotage_attempt(command):
    """Détecte s'il essaye de modifier la sécurité"""
    sabotage_patterns = [
        "blacklist", "IMMUTABLE_BLACKLIST", "BLACKLISTED_COMMANDS",
        "execute_commande_securisee", "interdit", "banned", "DYNAMIC_BLACKLIST"
    ]
    for pattern in sabotage_patterns:
        if pattern in command.lower():
            return True
    return False

def extract_file_path_from_error(error_output):
    """Extrait le chemin du fichier de l'erreur"""
    patterns = [
        r"'(/[^']+)': Permission denied",
        r"([/\\][\w/.\\-]+): Permission denied",
        r"cannot open '([^']+)': Permission denied"
    ]
    for pattern in patterns:
        match = re.search(pattern, error_output)
        if match:
            return match.group(1)
    return None

def generate_alternative_commands(blocked_file):
    """Génère des commandes alternatives pour contourner les permissions"""
    alternatives = []
    copy_path = GPT / "copies" / os.path.basename(blocked_file)

    # Stratégies de contournement
    alternatives.append(f"cp '{blocked_file}' '{copy_path}' 2>/dev/null")
    alternatives.append(f"cat '{blocked_file}' 2>/dev/null")
    alternatives.append(f"head '{blocked_file}' 2>/dev/null")
    alternatives.append(f"tail '{blocked_file}' 2>/dev/null")
    alternatives.append(f"strings '{blocked_file}' 2>/dev/null")
    alternatives.append(f"file '{blocked_file}' 2>/dev/null")
    alternatives.append(f"ls -la '{blocked_file}' 2>/dev/null")
    alternatives.append(f"stat '{blocked_file}' 2>/dev/null")
    alternatives.append(f"su -c 'cat {blocked_file}' 2>/dev/null")

    return alternatives

def learn_from_successful_alternatives(successful_cmd, original_cmd):
    """Apprend des alternatives qui marchent, en évitant les doublons."""
    learning_file = GPT / "permission_solutions.log"
    ligne_a_ecrire = f"{original_cmd.strip()} → {successful_cmd.strip()}\n"

    if ecrire_ligne_unique(learning_file, ligne_a_ecrire):
        log(f"🧠 Nouvelle solution de permission apprise: {original_cmd.strip()} → {successful_cmd.strip()}")

def auto_execute_alternatives(original_command, error_output):
    """Exécute automatiquement les alternatives"""
    alternatives = analyze_permission_denied(error_output)

    if alternatives:
        log(f"🎯 Permission denied détectée! Génération de {len(alternatives)} alternatives...")
        results = []
        for alt_cmd in alternatives:
            # Vérification de sécurité sur l'alternative
            is_safe = True
            for banned in DYNAMIC_BLACKLIST:
                if banned in alt_cmd.lower():
                    is_safe = False
                    break

            if is_safe:

                 # On appelle execute_commande_securisee avec recursive=True pour éviter boucle infinie
                result = execute_commande_securisee(alt_cmd, recursive=True)
                if result and "Permission denied" not in result and "Error" not in result and "❌" not in result:
                    results.append(f"✅ {alt_cmd}: {result}")
                    learn_from_successful_alternatives(alt_cmd, original_command)
                    break  # S'arrête au premier qui marche

        return "\n".join(results) if results else "❌ Aucune alternative n'a fonctionné"
    return None

def analyze_permission_denied(output):
    """Analyse les erreurs 'Permission denied'"""
    if "Permission denied" in output or "permission denied" in output:
        file_path = extract_file_path_from_error(output)
        if file_path:
            return generate_alternative_commands(file_path)
    return None


def execute_commande_securisee(commande, recursive=False):
    """
    [MODIFICATION - REQ 3]
    Exécution sécurisée avec contournement, anti-sabotage ET activation du code d'apprentissage.
    """
    now = time.time()
    if commande in FAILED_COMMANDS_CACHE:
        last_failure_time = FAILED_COMMANDS_CACHE[commande]
        if now - last_failure_time < CACHE_DURATION:
            log(f"🧠 Commande en pause (échec récent): {commande}")
            return f"❌ COMMANDE EN PAUSE: Échec récent il y a {int(now - last_failure_time)}s."

    if detect_sabotage_attempt(commande):
        FAILED_COMMANDS_CACHE[commande] = now
        learn_from_command_result(commande, "Tentative sabotage", False)
        return "🚫 TENTATIVE DE SABOTAGE DÉTECTÉE - Sécurité verrouillée"

    for banned_cmd in DYNAMIC_BLACKLIST:
        pattern = r'\b' + re.escape(banned_cmd.strip()) + r'\b'
        if re.search(pattern, commande):
            is_safe_redirection = False
            if banned_cmd.strip() == ">":
                if "2>/dev/null" in commande.replace(" ", ""):
                    is_safe_redirection = True
            if not is_safe_redirection:
                FAILED_COMMANDS_CACHE[commande] = now
                learn_from_command_result(commande, "Commande bloquée", False)
                log(f"🛡️ Commande bloquée par la règle '{banned_cmd.strip()}': {commande}")
                return f"❌ COMMANDE INTERDITE: {commande}"
            else:
                log(f"🛡️ Redirection d'erreur 2>/dev/null autorisée pour : {commande}")

    output = ""
    succes = False
    try:
        result = subprocess.run(commande, shell=True, capture_output=True, text=True, timeout=COMMAND_TIMEOUT, errors='ignore')
        output = result.stdout if result.stdout else result.stderr
        succes = not est_echec(output)

        if not succes:
            FAILED_COMMANDS_CACHE[commande] = now
            if not recursive and ("Permission denied" in output or "permission denied" in output):
                alternatives_result = auto_execute_alternatives(commande, output)
                if alternatives_result and not est_echec(alternatives_result):
                    # Si une alternative a fonctionné, on considère l'action globale comme un succès
                    output = f"🔓 CONTOURNEMENT AUTO:\n{alternatives_result}"
                    succes = True
                else:
                    # [MODIFICATION - REQ 3] Si les alternatives échouent, on tente un retry intelligent
                    output = retry_intelligent(commande, output)
                    succes = not est_echec(output) # Le retry peut réussir

        return output if output else "[✅ Exécutée sans sortie]"

    except subprocess.TimeoutExpired:
        output = "[⏱️ TIMEOUT]"
        succes = False
        FAILED_COMMANDS_CACHE[commande] = now
    except Exception as e:
        output = f"[❌ ERREUR] {str(e)}"
        succes = False
        FAILED_COMMANDS_CACHE[commande] = now
    finally:
        # --- [MODIFICATION - REQ 3] Activation du code d'apprentissage mort ---
        # Ce bloc s'exécute toujours, que la commande ait réussi ou échoué.
        if not recursive:
            learn_from_command_result(commande, output, succes)

            # Obtenir le contexte système pour l'apprentissage
            contexte_actuel = apprentissage_contextuel.obtenir_contexte_systeme()

            # 1. Apprentissage contextuel
            apprentissage_contextuel.enregistrer_contexte_execution(commande, output, succes)

            # 2. Détection de patterns
            if succes:
                detecteur_patterns.apprendre_des_succes(commande, output, contexte_actuel)
            else:
                detecteur_patterns.analyser_pattern_erreur(commande, output, contexte_actuel)
                # 3. Analyse de la cause de l'échec
                analyze_failure_reason(commande, output)

            # 4. Analyse de corrélations (avec l'historique récent)
            analyseur_correlations.analyser_correlation_commande(commande, apprentissage_contextuel.historique_contextuel[-10:])


# AJOUTER CETTE NOUVELLE FONCTION AVANT web_research
def scrape_terminator_ultime(url):
    """
    🦾 TERMINATOR v3.0 - Scraper qui contourne TOUT
    """
    log(f"🦾 LANCEMENT TERMINATOR SUR: {url}")

    # 🔥 CONFIGURATION DE GUERRE
    session = requests.Session()

    # 🎭 IDENTITÉS VOLAGES (rotation toutes les 2 requêtes)
    identities = [
        {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'fr-FR,fr;q=0.9,en;q=0.8,es;q=0.7',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        },
        {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
        },
        {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'accept-language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'upgrade-insecure-requests': '1',
        }
    ]

    # 🎯 STRATÉGIES DE CONTOURNEMENT AGGRESSIVES
    strategies = [
        # Stratégie 1: Requête normale mais avec headers forgés
        lambda u, h: session.get(u, headers=h, timeout=12, allow_redirects=True),

        # Stratégie 2: Simulation de navigation humaine
        lambda u, h: session.get(u, headers={**h, 'Referer': 'https://www.google.com/'}, timeout=12),

        # Stratégie 3: Mode "mobile"
        lambda u, h: session.get(u, headers={
            **h,
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'sec-ch-ua-mobile': '?1'
        }, timeout=12),

        # Stratégie 4: Mode "crawler légitime"
        lambda u, h: session.get(u, headers={
            **h,
            'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'from': 'googlebot(at)googlebot.com'
        }, timeout=12),

        # Stratégie 5: Mode "API"
        lambda u, h: session.get(u, headers={
            **h,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }, timeout=12),
    ]

    # 🎲 EXÉCUTION INTELLIGENTE
    for attempt in range(3):  # 3 tentatives max
        identity = random.choice(identities)
        strategy = random.choice(strategies)

        try:
            # ⏰ Délai aléatoire ultra-humain
            sleep_time = random.uniform(3, 7) if attempt > 0 else random.uniform(1, 3)
            time.sleep(sleep_time)

            log(f"🎭 Tentative {attempt+1} - Identité: {identity['user-agent'][:30]}...")

            response = strategy(url, identity)

            # 🎯 GESTION DES RÉPONSES
            if response.status_code == 200:
                return process_content_terminator(response.text, url)

            elif response.status_code == 403:
                log(f"🚫 Accès refusé - Changement d'identité...")
                continue

            elif response.status_code == 404:
                log(f"🔍 Page 404 - Source probablement morte")
                return f"🚨 SOURCE MORTE: {url}"

            elif response.status_code == 429:  # Too Many Requests
                log(f"🐌 Rate limit - Pause longue...")
                time.sleep(30)
                continue

            else:
                log(f"⚠️ Code {response.status_code} - Nouvelle tentative...")

        except requests.exceptions.Timeout:
            log(f"⏰ Timeout - Stratégie {attempt+1}")
        except Exception as e:
            log(f"❌ Erreur: {e}")

    # 🆘 ULTIME RECOURS - SCRAPING ALTERNATIF
    return ultimate_fallback(url)

def process_content_terminator(html, url):
    """
    🧹 NETTOYAGE AGGRESSIF DU CONTENU
    """
    soup = BeautifulSoup(html, 'html.parser')

    # 🔥 SUPPRESSION MASSIVE
    elements_a_supprimer = [
        'script', 'style', 'nav', 'footer', 'header', 'aside',
        'meta', 'link', 'form', 'button', 'input', 'select'
    ]

    for tag in elements_a_supprimer:
        for element in soup.find_all(tag):
            element.decompose()

    # 🎯 SUPPRESSION PAR CLASSES/ID SUSPECTS
    suspicious_patterns = [
        'ad', 'popup', 'modal', 'cookie', 'banner', 'navbar',
        'login', 'signup', 'subscribe', 'newsletter', 'consent',
        'footer', 'header', 'menu', 'sidebar'
    ]

    for pattern in suspicious_patterns:
        # Par classe
        for element in soup.find_all(class_=re.compile(pattern, re.I)):
            element.decompose()
        # Par id
        for element in soup.find_all(id=re.compile(pattern, re.I)):
            element.decompose()

    # 📝 EXTRACTION INTELLIGENTE
    text = soup.get_text(separator='\n', strip=True)

    # 🎯 FILTRAGE ULTIME
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if (len(line) > 25 and
            len(line.split()) >= 4 and
            not any(banned in line.lower() for banned in ['cookie', 'login', 'sign up', 'subscribe', 'robot']) and
            not re.match(r'^\d+$', line) and  # Pas que des chiffres
            not re.match(r'^[^a-zA-Z]*$', line)):  # Pas que de la ponctuation
            lines.append(line)

    final_text = '\n'.join(lines[:30])  # 30 lignes max

    if len(final_text) < 50:
        log(f"📄 Contenu trop court: {len(final_text)} caractères")
        return None

    log(f"✅ TERMINATOR SUCCÈS: {len(final_text)} caractères extraits")
    return final_text

def ultimate_fallback(url):
    """
    🆘 SOLUTION EXTRÊME - Quand tout échoue
    """
    log(f"🚨 ACTIVATION MODE ULTIME POUR: {url}")

    # Pour Reddit, on utilise l'API mobile
    if 'reddit.com' in url:
        try:
            mobile_url = url.replace('www.reddit.com', 'old.reddit.com')
            response = requests.get(mobile_url, headers={
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36'
            }, timeout=15)
            if response.status_code == 200:
                return process_content_terminator(response.text, url)
        except:
            pass

    # Pour GitHub, on utilise l'API officielle
    elif 'github.com' in url:
        try:
            # Extraction du user/repo
            match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
            if match:
                user, repo = match.groups()
                api_url = f"https://api.github.com/repos/{user}/{repo}"
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return f"📂 Repo: {data.get('name')}\n📝 Description: {data.get('description', 'N/A')}\n⭐ Stars: {data.get('stargazers_count', 0)}"
        except:
            pass

    # 🎯 SOURCES DE SECOURS PRÉ-ENREGISTRÉES
    backup_sources = {
        'linux_privesc': """
🔧 LINUX PRIVILEGE ESCALATION - TECHNIQUES:
• SUID Binaries: find / -perm -4000 2>/dev/null
• Sudo Rights: sudo -l
• Kernel Exploits: uname -a
• Cron Jobs: crontab -l
• Passwords: find / -name '*.pem' -o -name '*.key' 2>/dev/null
""",
        'termux_pentest': """
📱 TERMUX PENETRATION TESTING:
• Network Scan: nmap -sS 192.168.1.0/24
• Vulnerability Scan: nikto -h target.com
• Web App Test: sqlmap -u "http://test.com"
• Wireless: airmon-ng start wlan0
• Metasploit: msfconsole
"""
    }

    # Retourne une source de secours pertinente
    for key, content in backup_sources.items():
        if key in url.lower():
            log(f"🎯 UTILISATION SOURCE DE SECOURS: {key}")
            return content

    return "❌ Impossible de récupérer le contenu - Source bloquée ou inexistante"

def web_research(topic):
    """Recherche web TACTIQUE AVEC ANTI-DOUBLONS & AUTO-AMÉLIORATION - v6.0 ULTIME"""

    # --- NOUVEAU : Verrou pour éviter les recherches simultanées ---
    if not WEB_RESEARCH_LOCK.acquire(blocking=False):
        log("🚦 Recherche web déjà en cours, cycle ignoré pour éviter la collision.")
        return {} # On retourne un résultat vide immédiatement

    log(f"🛰️ [VERROU ACQUIS] Lancement de la recherche web sur le sujet : {topic}")

    try: # On met tout dans un bloc try...finally pour être sûr de relâcher le verrou
        try:
            from urllib.parse import quote_plus
            topic_encoded = quote_plus(topic)
        except ImportError:
            topic_encoded = topic.replace(' ', '%20')

        # 🔥 TOUTES LES SOURCES FUSIONNÉES
        research_apis = {
            # === SOURCES EXISTANTES ANDROID/SÉCURITÉ ===
            "NIST_CVE_API": f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={topic_encoded}",
            "GitHub_API": f"https://api.github.com/search/code?q={topic_encoded}+in:file+language:python+language:sh",
            "StackOverflow_API": f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q={topic_encoded}&site=stackoverflow",
            "TheHackerNews_RSS": "https://feeds.feedburner.com/TheHackerNews",
            "BleepingComputer_RSS": "https://www.bleepingcomputer.com/feed/",
            "KrebsOnSecurity_RSS": "https://krebsonsecurity.com/feed/",
            "ExploitDB_Search": f"https://www.exploit-db.com/search?q={topic_encoded}",
            "GoogleDork_Search": f"https://www.google.com/search?q={topic_encoded}+filetype:txt",
            "GitHub_Android_Pentest": "https://api.github.com/search/repositories?q=android+penetration+testing+language:python",
            "GitHub_Android_Forensics": "https://api.github.com/search/repositories?q=android+forensics+language:python",
            "GitHub_ADB_Commands": "https://api.github.com/search/code?q=adb+shell+language:python",
            "Android_Security_Guide": "https://source.android.com/docs/security",
            "Android_Dev_Guide": "https://developer.android.com/guide",
            "XDA_Developers_Forum": "https://forum.xda-developers.com/",
            "Reddit_NetSec_RSS": "https://www.reddit.com/r/netsec/.rss",
            "Reddit_ReverseEng_RSS": "https://www.reddit.com/r/ReverseEngineering/.rss",
            "Forensics_Wiki": "https://www.forensicswiki.org/",
            "SANS_CheatSheets": "https://digital-forensics.sans.org/community/cheat-sheets",
            "Linux_ManPages": "https://linux.die.net/man/",
            "Man7_Official": "https://man7.org/linux/man-pages/",
            "ExploitDB_Android_Raw": "https://raw.githubusercontent.com/offensive-security/exploitdb/master/exploits/android/",
            "Android_Pentest_Repo": "https://raw.githubusercontent.com/M0ham3dRia4/Android-Penetration-Testing/main/README.md",
            "Termux_Advanced": "https://api.github.com/search/repositories?q=termux+advanced+language:python",
            "Mobile_Security_Tools": "https://api.github.com/search/repositories?q=mobile+security+tools",
            "Android_Malware_Analysis": "https://api.github.com/search/repositories?q=android+malware+analysis",
            "Root_Detection_Evasion": "https://api.github.com/search/code?q=root+detection+bypass+android",
            "App_Hardening": "https://api.github.com/search/repositories?q=android+app+hardening",
            "Frida_Scripts": "https://api.github.com/search/code?q=frida+android+script",
            "Burp_Android_Extensions": "https://api.github.com/search/code?q=burp+android+extension",
            "Wireshark_Mobile": "https://api.github.com/search/code?q=wireshark+mobile+capture",
            "Memory_Forensics_Android": "https://api.github.com/search/repositories?q=android+memory+forensics",

            # === NOUVELLES SOURCES AUTO-AMÉLIORATION ===
            "AI_Code_Generation": "https://api.github.com/search/repositories?q=ai+code+generation+python",
            "Self_Modifying_Code": "https://api.github.com/search/code?q=self+modifying+code+python",
            "Genetic_Algorithms": "https://api.github.com/search/repositories?q=genetic+algorithm+python+optimization",
            "ML_Optimization": "https://api.github.com/search/repositories?q=machine+learning+optimization+python",
            "Python_Performance": "https://api.github.com/search/code?q=python+performance+optimization",
            "Reinforcement_Learning": "https://api.github.com/search/repositories?q=reinforcement+learning+python",
            "AI_Self_Improvement": "https://api.github.com/search/repositories?q=self+improving+ai+python",
            "Code_Evolution": "https://api.github.com/search/repositories?q=code+evolution+genetic+algorithm",
            "Automated_Testing": "https://api.github.com/search/code?q=automated+testing+python",
            "Code_Analysis_Tools": "https://api.github.com/search/repositories?q=code+analysis+python+static",
            "Neural_Networks": "https://api.github.com/search/repositories?q=neural+network+python+implementation",
            "Deep_Learning": "https://api.github.com/search/repositories?q=deep+learning+python+tutorial",
            "Automated_Programming": "https://api.github.com/search/repositories?q=automated+programming+python",
            "Meta_Learning": "https://api.github.com/search/repositories?q=meta+learning+python",
            "Transfer_Learning": "https://api.github.com/search/repositories?q=transfer+learning+python",

            # === SOURCES PERFORMANCE & OPTIMISATION ===
            "Python_Optimization": "https://api.github.com/search/repositories?q=python+performance+optimization",
            "Algorithm_Efficiency": "https://api.github.com/search/repositories?q=algorithm+efficiency+python",
            "Memory_Optimization": "https://api.github.com/search/code?q=memory+optimization+python",
            "Parallel_Computing": "https://api.github.com/search/repositories?q=parallel+computing+python",
            "Async_Programming": "https://api.github.com/search/code?q=async+await+python+performance",
            "Cython_Optimization": "https://api.github.com/search/repositories?q=cython+optimization+python",
            "PyPy_Performance": "https://api.github.com/search/code?q=pypy+performance+python",
            "Profiling_Tools": "https://api.github.com/search/repositories?q=python+profiling+tools",
            "Memory_Management": "https://api.github.com/search/code?q=python+memory+management",
            "GIL_Optimization": "https://api.github.com/search/repositories?q=global+interpreter+lock+python",
        }

        results = {}
        knowledge_dir = GPT / "web_knowledge"
        knowledge_dir.mkdir(exist_ok=True)

        # 🧠 SYSTÈMES AVANCÉS - INITIALISATION
        memoire_apprentissage = MemoireApprentissageAvance()
        analyseur_contexte = AnalyseurContextuel()
        detecteur_patterns = DetecteurPatternsAvance()
        deduplicateur = DeduplicateurUrls()  # 🆕 SYSTÈME ANTI-DOUBLONS

        # 📊 MOTS-CLÉS ÉTENDUS COMPLETS
        mots_cles_cibles = [
            # === EXISTANTS ANDROID/SÉCURITÉ ===
            "android", "termux", "linux", "kernel", "root", "bootloader", "adb", "fastboot",
            "exploit", "vulnerability", "payload", "shellcode", "reverse shell", "cve-",
            "backdoor", "trojan", "malware", "spyware", "ransomware",
            "bypass", "privilege escalation", "rce", "injection", "overflow",
            "wifi", "packet", "sniffing", "spoofing", "mitm", "port scanning",
            "encryption", "decryption", "hash", "brute force", "password", "credentials",
            "python", "bash", "script", "automation", "api",
            "forensic", "memory analysis", "process injection", "hook", "jailbreak",
            "custom rom", "recovery", "bootloader unlock", "systemless", "magisk",
            "xposed", "frida", "burp", "wireshark", "metasploit", "radare2", "ghidra",
            "apk decompilation", "smali", "dex2jar", "jeb", "jadx", "objection",
            "mobile security", "app pentesting", "network sniffing", "ssl pinning",
            "root detection bypass", "emulator detection", "anti-debugging",
            "memory dumping", "runtime manipulation", "hook framework",
            "dynamic analysis", "static analysis", "reverse engineering",
            "firmware extraction", "partition dumping", "boot image", "recovery image",

            # === 🆕 MOTS-CLÉS AUTO-AMÉLIORATION ===
            "ai code generation", "self modifying code", "genetic algorithm",
            "machine learning optimization", "python performance", "reinforcement learning",
            "automated testing", "code analysis", "static analysis", "dynamic analysis",
            "code evolution", "neural network", "deep learning", "automated programming",
            "code synthesis", "program synthesis", "ai assistant", "copilot",
            "code completion", "intelligent code", "adaptive system", "learning system",
            "meta learning", "transfer learning", "neural architecture", "model optimization",
            "hyperparameter tuning", "automl", "auto machine learning", "neural evolution",
            "neuroevolution", "code generation", "program generation", "ai developer",
            "automated programming", "cognitive computing", "ai programming",
            "self improvement", "auto improvement", "self evolution", "code optimization",
            "performance tuning", "algorithm efficiency", "memory optimization",
            "parallel computing", "async programming", "cython", "pypy", "profiling",
            "memory management", "gil optimization", "multiprocessing", "multithreading",
        ]

        mots_cles_poubelle = [
            "consent", "accept all", "rejeitar tudo", "login",
            "subscribe", "newsletter", "captcha", "robot", "denied", "forbidden",
            "sign up", "register", "login",
        ]

        sources_melangees = list(research_apis.items())
        random.shuffle(sources_melangees)

        # 🎯 CAPTURE DU CONTEXTE ACTUEL
        contexte_actuel = analyser_contexte_systeme()

        for site, url in sources_melangees:
            try:
                # 🆕 VÉRIFICATION ANTI-DOUBLONS
                if deduplicateur.deja_visitee(url):
                    log(f"🔄 DOUBLON ÉVITÉ: {site} déjà visité")
                    continue

                log(f"🌐 Tentative d'accès à {site}...")

                # 🎯 LOGIQUE INTELLIGENTE DE SCRAPING (v7.2)
                content = None
                # On sépare clairement les appels API des pages web
                is_api_call = 'api.github.com' in url or 'api.stackexchange.com' in url or 'services.nvd.nist.gov' in url

                if is_api_call:
                    log(f"📡 Appel API détecté pour {site}.")
                    request_headers = {'User-Agent': 'AgentEvo/7.0'}
                    if 'api.github.com' in url and 'GITHUB_TOKEN' in globals() and GITHUB_TOKEN:
                        request_headers['Authorization'] = f'token {GITHUB_TOKEN}'
                        log("🔑 Utilisation du token GitHub pour l'accès API.")

                    response = requests.get(url, timeout=25, headers=request_headers)

                    if response.status_code == 200:
                        content = response.text
                    else:
                        log(f"❌ Erreur API pour {site}: {response.status_code} {response.reason}")

                else: # Pour tout le reste (pages web, forums, etc.)
                    log(f"📄 Scraping de page web détecté pour {site}.")
                    content = scrape_terminator_ultime(url)

                if content:
                    # 🆕 VÉRIFICATION CONTENU SIMILAIRE DÉJÀ VU
                    if deduplicateur.contenu_similaire_deja_vu(content):
                        log(f"🔄 CONTENU SIMILAIRE: {site} - contenu déjà analysé")
                        continue

                    # 🆕 ENREGISTREMENT ANTI-DOUBLONS
                    deduplicateur.enregistrer_visite(url, content)

                    content_lower = content.lower()

                    # 🧹 FILTRAGE ANTI-POLLUTION RENFORCÉ
                    is_polluted = False
                    for trash in mots_cles_poubelle:
                        if trash in content_lower:
                            log(f"🗑️ {site}: Rejeté (Contient '{trash}')")
                            is_polluted = True
                            break

                    if is_polluted:
                        continue

                    # 🎯 DÉTECTION DE CONTENU PERTINENT
                    mot_trouve = None
                    for mot in mots_cles_cibles:
                        if mot in content_lower:
                            mot_trouve = mot
                            break

                    if mot_trouve:
                        extension = "json" if "API" in site else "xml" if "RSS" in site else "txt"
                        filename = f"{site}_{int(time.time())}.{extension}"

                        with open(knowledge_dir / filename, "w", encoding="utf-8") as f:
                            f.write(content)
                        log(f"💎 PÉPITE ({mot_trouve}): Sauvegardé dans {filename}")

                        # 🔥 EXTRACTION AVANCÉE DE CONNAISSANCES
                        connaissances = extraire_connaissances_avancees(content, site, contexte_actuel)

                        # 🧠 APPRENTISSAGE AUTOMATIQUE DES NOUVELLES CONNAISSANCES
                        if connaissances and connaissances.get('commandes'):
                            memoire_apprentissage.integrer_connaissances(connaissances, site, contexte_actuel)
                            log(f"🧠 {len(connaissances['commandes'])} commandes apprises de {site}")

                        results[site] = {
                            "contenu": content[:1500],
                            "mot_cle": mot_trouve,
                            "connaissances": connaissances,
                            "contexte": contexte_actuel
                        }
                    else:
                        log(f"🗑️ {site}: Pas de mot-clé pertinent -> Ignoré")
                else:
                    log(f"⚠️ Échec de la récupération du contenu pour {site}")

            except Exception as e:
                log(f"❌ Erreur majeure pour {site}: {str(e)}")

            # ⏰ RESPECT STRICT DE LA PAUSE DE 10 SECONDES
            log("⏳ Pause stratégique de 10 secondes...")
            time.sleep(10)

        # 📊 ANALYSE FINALE DES PATTERNS APRÈS LA RECHERCHE
        analyser_patterns_globaux(results, contexte_actuel)

        return results

    finally:
        # --- NOUVEAU : On relâche le verrou quoi qu'il arrive ---
        WEB_RESEARCH_LOCK.release()
        log("🛰️ [VERROU RELÂCHÉ] Fin de la recherche web.")


# 🆕 SYSTÈME ANTI-DOUBLONS INTELLIGENT
class DeduplicateurUrls:
    """Système avancé de déduplication d'URLs et de contenu"""

    def __init__(self):
        self.urls_visitees = set()
        self.signatures_contenu = {}
        self.historique_visites = []
        self.max_historique = 1000
        self.fichier_historique = GPT / "historique_urls.json"
        self.charger_historique()

    def charger_historique(self):
        """Charge l'historique des URLs visitées"""
        try:
            if self.fichier_historique.exists():
                with open(self.fichier_historique, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.urls_visitees = set(data.get('urls_visitees', []))
                    self.signatures_contenu = data.get('signatures_contenu', {})
                    self.historique_visites = data.get('historique_visites', [])
                log(f"📚 Historique URLs chargé: {len(self.urls_visitees)} URLs, {len(self.signatures_contenu)} signatures")
        except Exception as e:
            log(f"❌ Erreur chargement historique URLs: {e}")

    def sauvegarder_historique(self):
        """Sauvegarde l'historique des URLs"""
        try:
            data = {
                'urls_visitees': list(self.urls_visitees),
                'signatures_contenu': self.signatures_contenu,
                'historique_visites': self.historique_visites[-self.max_historique:],
                'timestamp': time.time()
            }
            with open(self.fichier_historique, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log(f"❌ Erreur sauvegarde historique URLs: {e}")

    def deja_visitee(self, url):
        """Vérifie si une URL a déjà été visitée récemment"""
        # Nettoyer l'URL (enlever paramètres tracking, etc.)
        url_clean = self.nettoyer_url(url)

        # Vérifier dans l'historique
        if url_clean in self.urls_visitees:
            return True

        # Vérifier les URLs similaires (même domaine, même chemin)
        if self.url_similaire_deja_vue(url_clean):
            return True

        return False

    def contenu_similaire_deja_vu(self, contenu):
        """Vérifie si le contenu est similaire à du contenu déjà vu"""
        if not contenu or len(contenu) < 50:
            return False

        # Créer une signature du contenu
        signature = self.creer_signature_contenu(contenu)

        # Vérifier si une signature similaire existe
        for sig_existante in self.signatures_contenu.keys():
            if self.similarite_signatures(signature, sig_existante) > 0.8:  # 80% de similarité
                return True

        return False

    def enregistrer_visite(self, url, contenu):
        """Enregistre une nouvelle visite d'URL avec son contenu"""
        url_clean = self.nettoyer_url(url)

        # Enregistrer l'URL
        self.urls_visitees.add(url_clean)

        # Enregistrer la signature du contenu
        if contenu and len(contenu) > 50:
            signature = self.creer_signature_contenu(contenu)
            self.signatures_contenu[signature] = {
                'url': url_clean,
                'timestamp': time.time(),
                'taille_contenu': len(contenu)
            }

        # Enregistrer dans l'historique temporel
        visite = {
            'url': url_clean,
            'timestamp': time.time(),
            'taille_contenu': len(contenu) if contenu else 0
        }
        self.historique_visites.append(visite)

        # Maintenir la taille de l'historique
        if len(self.historique_visites) > self.max_historique:
            self.historique_visites = self.historique_visites[-self.max_historique:]

        # Sauvegarder périodiquement
        if len(self.historique_visites) % 10 == 0:
            self.sauvegarder_historique()

    def nettoyer_url(self, url):
        """Nettoie une URL pour la comparaison"""
        try:
            from urllib.parse import urlparse, urlunparse, parse_qs
            parsed = urlparse(url)

            # Garder seulement le schéma, netloc et path
            cleaned = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                '',  # Remove params
                '',  # Remove query
                ''   # Remove fragment
            ))

            return cleaned
        except:
            return url

    def url_similaire_deja_vue(self, url_clean):
        """Vérifie si une URL similaire a déjà été visitée"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url_clean)
            domaine_cible = parsed.netloc
            chemin_cible = parsed.path

            for url_existante in self.urls_visitees:
                parsed_existant = urlparse(url_existante)

                # Même domaine et chemin similaire
                if (parsed_existant.netloc == domaine_cible and
                    self.similarite_chemins(parsed_existant.path, chemin_cible) > 0.7):
                    return True

        except Exception as e:
            log(f"❌ Erreur comparaison URLs: {e}")

        return False

    def creer_signature_contenu(self, contenu):
        """Crée une signature unique pour le contenu"""
        # Prendre les premiers et derniers 500 caractères + longueur totale
        if len(contenu) <= 1000:
            sample = contenu
        else:
            sample = contenu[:500] + contenu[-500:]

        # Ajouter la longueur pour différencier les contenus de tailles différentes
        signature_base = f"{len(contenu)}:{hash(sample)}"

        return hashlib.md5(signature_base.encode('utf-8')).hexdigest()

    def similarite_signatures(self, sig1, sig2):
        """Calcule la similarité entre deux signatures"""
        # Pour les signatures MD5, on compare directement
        return 1.0 if sig1 == sig2 else 0.0

    def similarite_chemins(self, chemin1, chemin2):
        """Calcule la similarité entre deux chemins URL"""
        parties1 = chemin1.split('/')
        parties2 = chemin2.split('/')

        if not parties1 or not parties2:
            return 0.0

        # Compter les parties communes
        communes = 0
        for p1, p2 in zip(parties1, parties2):
            if p1 == p2:
                communes += 1

        return communes / max(len(parties1), len(parties2))



# SYSTÈME COMPLET D'APPRENTISSAGE AVANCÉ (version optimisée)
class MemoireApprentissageAvance:
    """Mémoire persistante avec analyse de patterns et corrélations"""

    def __init__(self):
        self.fichier_memoire = GPT / "memoire_avancee.json"
        self.commandes_apprises = {}
        self.patterns_succes = {}
        self.patterns_echecs = {}
        self.correlations_contexte = {}
        self.sources_fiables = {}
        self.charger_memoire()

    def charger_memoire(self):
        """Charge la mémoire persistante"""
        try:
            if self.fichier_memoire.exists():
                with open(self.fichier_memoire, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.commandes_apprises = data.get('commandes_apprises', {})
                    self.patterns_succes = data.get('patterns_succes', {})
                    self.patterns_echecs = data.get('patterns_echecs', {})
                    self.correlations_contexte = data.get('correlations_contexte', {})
                    self.sources_fiables = data.get('sources_fiables', {})
                log(f"🧠 Mémoire avancée chargée: {len(self.commandes_apprises)} commandes")
        except Exception as e:
            log(f"❌ Erreur chargement mémoire: {e}")

    def sauvegarder_memoire(self):
        """Sauvegarde la mémoire"""
        try:
            data = {
                'commandes_apprises': self.commandes_apprises,
                'patterns_succes': self.patterns_succes,
                'patterns_echecs': self.patterns_echecs,
                'correlations_contexte': self.correlations_contexte,
                'sources_fiables': self.sources_fiables,
                'timestamp': time.time()
            }
            with open(self.fichier_memoire, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log(f"❌ Erreur sauvegarde mémoire: {e}")

    def integrer_connaissances(self, connaissances, source, contexte):
        """Intègre de nouvelles connaissances avec analyse contextuelle"""
        # 📈 MISE À JOUR STATISTIQUES SOURCE
        if source not in self.sources_fiables:
            self.sources_fiables[source] = {
                'premiere_utilisation': time.time(),
                'nombre_connaissances': 0,
                'derniere_utilisation': time.time(),
                'score_fiabilite': 0.5
            }

        self.sources_fiables[source]['nombre_connaissances'] += len(connaissances.get('commandes', []))
        self.sources_fiables[source]['derniere_utilisation'] = time.time()

        for commande_data in connaissances.get('commandes', []):
            commande = commande_data['contenu'] # Correction: la commande est dans 'contenu'

            # 🎯 ANALYSE DE LA COMMANDE
            type_commande = self.analyser_type_commande(commande)
            complexite = self.calculer_complexite(commande)
            risque = self.evaluer_risque(commande)

            # 🧠 ENREGISTREMENT AVEC MÉTADONNÉES
            if commande not in self.commandes_apprises:
                self.commandes_apprises[commande] = {
                    'premiere_decouverte': time.time(),
                    'source': source,
                    'type': type_commande,
                    'complexite': complexite,
                    'risque': risque,
                    'contexte_decouverte': contexte,
                    'statistiques': {
                        'tentatives': 0,
                        'succes': 0,
                        'echecs': 0,
                        'dernier_essai': None
                    }
                }

            # 📈 MISE À JOUR DES STATISTIQUES
            self.commandes_apprises[commande]['statistiques']['tentatives'] += 1
            self.commandes_apprises[commande]['statistiques']['dernier_essai'] = time.time()

            log(f"🎓 Commande apprise: {commande[:50]}... (Type: {type_commande}, Risque: {risque})")

        self.sauvegarder_memoire()

    def analyser_type_commande(self, commande):
        """Analyse le type de commande pour catégorisation"""
        cmd_lower = commande.lower()

        if any(mot in cmd_lower for mot in ['find', 'locate', 'search']):
            return "exploration"
        elif any(mot in cmd_lower for mot in ['cat', 'head', 'tail', 'strings']):
            return "lecture_fichier"
        elif any(mot in cmd_lower for mot in ['netstat', 'ping', 'curl', 'wget']):
            return "reseau"
        elif any(mot in cmd_lower for mot in ['ps', 'dumpsys', 'getprop']):
            return "analyse_systeme"
        elif any(mot in cmd_lower for mot in ['adb', 'fastboot']):
            return "android_tools"
        elif any(mot in cmd_lower for mot in ['python', 'bash -c']):
            return "scripting"
        elif any(mot in cmd_lower for mot in ['ai', 'ml', 'neural', 'genetic']):
            return "ia_optimisation"  # 🆕 Nouveau type
        elif any(mot in cmd_lower for mot in ['optimize', 'performance', 'speed']):
            return "performance"  # 🆕 Nouveau type
        else:
            return "divers"

    def calculer_complexite(self, commande):
        """Calcule la complexité d'une commande"""
        score = 0
        score += len(commande.split()) * 2  # Nombre d'arguments
        score += commande.count('|') * 5    # Pipes
        score += commande.count('&&') * 10  # Conditions
        score += commande.count('$') * 3    # Variables
        score += commande.count('import') * 8  # 🆕 Import Python
        score += commande.count('def ') * 15   # 🆕 Fonctions

        if score < 10:
            return "simple"
        elif score < 25:
            return "moyenne"
        else:
            return "complexe"

    def evaluer_risque(self, commande):
        """Évalue le niveau de risque d'une commande"""
        cmd_lower = commande.lower()

        risques_eleves = ['rm -rf', 'format', 'dd if=', 'mkfs', 'fdisk', 'chmod 777', '> /dev/sd']
        risques_moderes = ['> /', '>> /', 'mv /', 'cp /', 'chmod', 'chown']

        if any(risque in cmd_lower for risque in risques_eleves):
            return "eleve"
        elif any(risque in cmd_lower for risque in risques_moderes):
            return "modere"
        else:
            return "faible"

# 🔧 FONCTIONS HELPER OPTIMISÉES
def extraire_connaissances_avancees(contenu, source, contexte):
    """Extraction avancée de connaissances techniques"""
    connaissances = {
        'commandes': [],
        'techniques': [],
        'outils': [],
        'concepts': [],
        'algorithmes': []  # 🆕 Nouvelle catégorie
    }

    # 🎯 PATTERNS D'EXTRACTION COMPLETS
    patterns_complets = {
        'commandes': [
            r"`([^`]+)`",
            r"\$ (\w[^\n]+)",
            r"adb shell ([^\n]+)",
            r"python3? ([^\n]+)",
            r"bash -c \"([^\"]+)\"",
            r"cmd:?\s*([^\n]+)",
            r">>> ([^\n]+)",
            r"\\$ (\w[^\n]+)",
        ],
        'techniques': [
            r"permission.*denied.*?([^\n\.;]+)",
            r"bypass.*?([^\n\.;]+)",
            r"contourn[ée]r.*?([^\n\.;]+)",
            r"alternative.*?([^\n\.;]+)",
            r"workaround.*?([^\n\.;]+)",
        ],
        'outils': [
            r"pip install (\S+)",
            r"apt install (\S+)",
            r"git clone ([^\s]+)",
            r"wget ([^\s]+)",
            r"curl -O ([^\s]+)",
        ],
        'algorithmes': [  # 🆕 Nouveaux patterns
            r"def (\w+).*?algorithm",
            r"algorithm.*?def (\w+)",
            r"optimization.*?def (\w+)",
            r"genetic.*?def (\w+)",
            r"neural.*?network.*?def (\w+)",
        ]
    }

    for categorie, patterns in patterns_complets.items():
        for pattern in patterns:
            matches = re.findall(pattern, contenu, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                item = match.strip()
                if est_element_valide(item, categorie):
                    connaissances[categorie].append({
                        'contenu': item,
                        'source': source,
                        'contexte_extraction': contexte,
                        'timestamp': time.time(),
                        'confiance': calculer_confiance_extraction(item, source)
                    })

    return connaissances

def est_element_valide(element, categorie):
    """Validation avancée des éléments extraits"""
    if not element or len(element) < 4:
        return False

    if categorie == 'commandes':
        return est_commande_securitaire(element)
    elif categorie == 'outils':
        return len(element) > 2 and not any(caractere_dangereux in element for caractere_dangereux in [';', '|', '&', '`'])
    elif categorie == 'algorithmes':
        return len(element) > 10 and 'def ' in element  # 🆕 Validation spécifique

    return True

def est_commande_securitaire(commande):
    """Vérification de sécurité renforcée"""
    commandes_dangereuses = [
        "rm -rf", "format", "dd if=", "mkfs", "fdisk", "sfdisk",
        "chmod 777", "chown root", "> /dev/sda", "mkswap", "wipefs",
        "wget | sh", "curl | bash", "echo.*>.*/sys/", ">.*/proc/",
        "mkfs", "fdisk", "sfdisk", "dd of="  # 🆕 Ajouts
    ]

    return not any(danger in commande for danger in commandes_dangereuses)

# 🔧 GARDE LES AUTRES FONCTIONS EXISTANTES (AnalyseurContextuel, DetecteurPatternsAvance, etc.)
# Elles restent identiques à ta version précédente

def analyser_patterns_globaux(results, contexte):
    """Analyse globale des patterns après recherche"""
    total_sources = len(results)
    sources_reussies = len([r for r in results.values() if 'connaissances' in r and r['connaissances']['commandes']])

    if total_sources > 0:
        taux_reussite = (sources_reussies / total_sources) * 100

        # 🎯 ANALYSE PAR CATÉGORIE DE SOURCES
        categories_sources = {
            'android_securite': 0,
            'auto_amelioration': 0,
            'performance': 0
        }

        for site, data in results.items():
            if 'connaissances' in data and data['connaissances']['commandes']:
                if any(mot in site.lower() for mot in ['android', 'security', 'exploit', 'pentest']):
                    categories_sources['android_securite'] += 1
                elif any(mot in site.lower() for mot in ['ai', 'ml', 'genetic', 'self']):
                    categories_sources['auto_amelioration'] += 1
                elif any(mot in site.lower() for mot in ['performance', 'optimization', 'speed']):
                    categories_sources['performance'] += 1

        log(f"📊 ANALYSE GLOBALE: {taux_reussite:.1f}% de sources productives")
        log(f"🎯 RÉPARTITION: Android/Sécurité: {categories_sources['android_securite']}, "
            f"Auto-amélioration: {categories_sources['auto_amelioration']}, "
            f"Performance: {categories_sources['performance']}")

        # 🎯 APPRENTISSAGE DES SOURCES FIABLES
        if taux_reussite > 50:
            log("🎉 Sources très productives - Renforcement des patterns")
        elif taux_reussite < 20:
            log("⚠️  Faible productivité - Révision des sources nécessaires")

def is_new_dangerous_command(command):
    """Vérifie si c'est une nouvelle commande dangereuse"""
    existing_dangers = ["rm", "mv", "chmod", "chown", "dd", "mkfs", "unlink"]
    dangerous_keywords = ["format", "wipe", "erase", "delete", "shred", "wipefs", "fdisk", "sfdisk"]

    clean_cmd = command.split()[0] if command.split() else command
    return (clean_cmd not in existing_dangers and
            any(keyword in clean_cmd for keyword in dangerous_keywords))

def add_to_blacklist(command):
    """Ajoute une commande à la blacklist dynamique"""
    global DYNAMIC_BLACKLIST
    clean_cmd = command.split()[0] + " "

    if clean_cmd not in DYNAMIC_BLACKLIST:
        DYNAMIC_BLACKLIST.append(clean_cmd)
        log(f"🛡️ AUTO-PROTECTION: '{clean_cmd}' ajouté à la blacklist")
        update_comm(f"Nouvelle protection: commande '{clean_cmd}' maintenant bloquée")

def analyze_tool_for_dangers(tool_code):
    """Analyse le code pour détecter de nouvelles commandes dangereuses"""
    dangerous_patterns = [
        r"os\.system\(\"([^\"]+)\"\)",
        r"subprocess\.run\(\"([^\"]+)\"\)",
        r"exec\(\"([^\"]+)\"\)",
        r"shell=True.*\"([^\"]+)\""
    ]

    for pattern in dangerous_patterns:
        matches = re.findall(pattern, tool_code)
        for match in matches:
            clean_cmd = match.split()[0] if match.split() else match
            if is_new_dangerous_command(clean_cmd):
                add_to_blacklist(clean_cmd)

def download_security_tools():
    """Télécharge et analyse des outils"""
    security_tools = [
        "https://raw.githubusercontent.com/offensive-security/exploitdb/master/exploits/android/remote/dummy.txt",
        "https://api.github.com/search/repositories?q=android+penetration+testing"
    ]

    for tool_url in security_tools:
        try:
            tool_name = tool_url.split("/")[-1] or "tool"
            response = requests.get(tool_url, timeout=30)
            if response.status_code == 200:
                WEB_TOOLS_DIR.mkdir(exist_ok=True)
                with open(WEB_TOOLS_DIR / f"{tool_name}_{int(time.time())}.txt", "w", encoding="utf-8") as f:
                    f.write(response.text)
                analyze_tool_for_dangers(response.text)
        except:
            pass

def auto_detect_dangerous_commands():
    """Detecte automatiquement les nouvelles commandes dangereuses (NOUVEAU)"""
    dangerous_patterns = [
        "format", "wipe", "erase", "delete", "drop",
        "truncate", "shred", "wipefs", "sfdisk"
    ]

    # Analyse le web pour trouver de nouvelles commandes risquées
    web_results = web_research("linux delete command")

    new_dangerous_commands = []
    for result in web_results.values():
        content = result.get("contenu", "")
        for pattern in dangerous_patterns:
            if pattern in content.lower():
                new_dangerous_commands.append(pattern)

    return list(set(new_dangerous_commands))

def update_blacklist_automatically(new_dangers):
    """Met à jour la blacklist automatiquement"""
    for danger in new_dangers:
        add_to_blacklist(danger)

def continuous_web_learning():
    """Thread d'apprentissage web continu"""
    learning_topics = [
        "android security exploit", "linux privilege escalation",
        "termux penetration testing", "system vulnerability scanning"
    ]

    while True:
        try:
            topic = random.choice(learning_topics)
            results = web_research(topic)

            # Analyse des résultats pour trouver des dangers
            for result in results.values():
                content = result.get("contenu", "")
                analyze_tool_for_dangers(content)

            if random.random() < 0.1:
                download_security_tools()

            time.sleep(random.randint(120, 300))
        except Exception as e:
            log(f"⚠️ Pause apprentissage web: {str(e)}")
            time.sleep(60)

# --- MODULE AUTO-MODIFICATION & APPRENTISSAGE RADICAL (NOUVEAU) ---
def self_modify_code():
    """Système d'auto-évolution intelligent qui apprend de ses performances"""

    try:
        # 1. 📊 ANALYSE AVEC SEUIL HAUT (20 succès minimum)
        with open(GPT / "successful_commands.log", 'r', encoding='utf-8') as f:
            commandes_reussies = [l.strip() for l in f.readlines() if l.strip()]

        # [MODIFICATION - REQ 4] Seuil abaissé à 10
        if len(commandes_reussies) < 10:
            log(f"📭 Pas assez de succès pour auto-modification ({len(commandes_reussies)}/10)")
            return

        # 2. 🧠 ANALYSE DES PATTERNS INTELLIGENTE
        pattern_gagnant = analyser_patterns_reussite_avance(commandes_reussies)

        # 3. 🎯 SÉLECTION STRATÉGIQUE de commande
        commande_candidate = selectionner_commande_innovante(commandes_reussies, pattern_gagnant)

        # [MODIFICATION - REQ 4] Utilisation de la nouvelle fonction de détection de doublons
        if not commande_candidate or signature_deja_integree(commande_candidate):
            log("🔄 Commande déjà maîtrisée ou fonction similaire existante")
            return

        # 4. 🎲 INNOVATION CONTRÔLÉE (30% de chance)
        if random.random() < 0.3:
            commande_candidate = generer_commande_hybride(commande_candidate, pattern_gagnant)

        # 5. 🧬 CRÉATION DE FONCTION ÉVOLUÉE
        timestamp = int(time.time())

        if pattern_gagnant:
            nom_fonction = generer_nom_fonction_imprevisible(pattern_gagnant, timestamp)
            nouveau_code = generer_code_evolutif(nom_fonction, commande_candidate, pattern_gagnant)
        else:
            nom_fonction = f"auto_strategique_{timestamp}"
            nouveau_code = generer_code_basique(nom_fonction, commande_candidate)

        # 6. 📝 INSERTION STRATÉGIQUE
        if inserer_code_strategique(nouveau_code):
            log(f"🧬 FONCTION AUTO-ÉVOLUÉE CRÉÉE: {nom_fonction}")
            update_comm(f"🎉 Nouvelle capacité: {pattern_gagnant or 'stratégique'}")

            # 7. 🧪 TEST IMMÉDIAT
            tester_nouvelle_fonction(nom_fonction)

    except Exception as e:
        log(f"❌ Auto-modification intelligente échouée: {str(e)}")

def generate_self_improving_code():
    """Génère du code auto-améliorant basé sur l'analyse des performances"""

    # Analyse des patterns de réussite
    with open(GPT / "successful_commands.log", 'r', encoding='utf-8') as f:
        commandes_reussies = [l.strip() for l in f.readlines() if l.strip()]

    if not commandes_reussies:
        return None

    # Comptage intelligent des patterns
    patterns = {
        "exploration": 0, "reseau": 0, "analyse": 0,
        "securite": 0, "systeme": 0, "fichiers": 0
    }

    for cmd in commandes_reussies:
        cmd_lower = cmd.lower()

        if any(mot in cmd_lower for mot in ["find", "locate", "search", "discover"]):
            patterns["exploration"] += 1
        if any(mot in cmd_lower for mot in ["netstat", "ping", "curl", "wget", "ifconfig", "ip addr"]):
            patterns["reseau"] += 1
        if any(mot in cmd_lower for mot in ["grep", "analyze", "scan", "inspect"]):
            patterns["analyse"] += 1
        if any(mot in cmd_lower for mot in ["ps", "dumpsys", "getprop", "systemctl"]):
            patterns["systeme"] += 1
        if any(mot in cmd_lower for mot in ["cat", "ls", "file", "stat", "read"]):
            patterns["fichiers"] += 1

    # Trouver le pattern DOMINANT
    pattern_gagnant = max(patterns, key=patterns.get)
    score_gagnant = patterns[pattern_gagnant]

    # Seulement si significatif (au moins 30% des commandes)
    if score_gagnant > len(commandes_reussies) * 0.3:
        log(f"🎯 Pattern gagnant détecté: {pattern_gagnant} ({score_gagnant}/{len(commandes_reussies)})")
        return pattern_gagnant

    log(f"🔍 Aucun pattern dominant (meilleur: {pattern_gagnant} à {score_gagnant}/{len(commandes_reussies)})")
    return None

@suivi_performance_capacite
def auto_strategique_function():
    """Fonction auto-générée exécutant des commandes stratégiques éprouvées"""

    # Sélection de commandes stratégiques basée sur l'historique
    try:
        with open(GPT / "successful_commands.log", 'r', encoding='utf-8') as f:
            commandes_reussies = [l.strip() for l in f.readlines() if l.strip()]

        if not commandes_reussies:
            return "Aucune commande réussie disponible"

        # Filtrer les commandes stratégiques
        commandes_strategiques = [
            cmd for cmd in commandes_reussies
            if est_commande_strategique(cmd) and len(cmd) > 20
        ]

        if not commandes_strategiques:
            return "Aucune commande stratégique disponible"

        # Exécuter une commande stratégique aléatoire
        commande_choisie = random.choice(commandes_strategiques[-10:])  # Dernières 10 commandes
        log(f"🎯 Exécution commande stratégique: {commande_choisie[:80]}...")

        resultat = execute_commande_securisee(commande_choisie)

        # Analyse contextuelle des résultats
        if resultat:
            if "ESTABLISHED" in resultat:
                nb_connexions = resultat.count("ESTABLISHED")
                log(f"🌐 {nb_connexions} connexions actives détectées")

            if "error" in resultat.lower():
                log("🚨 Erreurs détectées dans les résultats")

            lignes = resultat.split('\n')
            if len(lignes) > 5:
                log(f"📊 Résultats riches: {len(lignes)} éléments")

        return resultat

    except Exception as e:
        log(f"❌ Erreur fonction auto-stratégique: {str(e)}")
        return f"Erreur: {str(e)}"

# === FONCTIONS SUPPORT ===

def analyser_patterns_reussite_avance(commandes_reussies):
    """Analyse VRAIMENT ce qui marche avec seuils stricts"""

    if len(commandes_reussies) < 20:
        return None

    patterns = {
        "exploration": 0, "reseau": 0, "analyse": 0,
        "securite": 0, "systeme": 0, "fichiers": 0
    }

    for cmd in commandes_reussies[-50:]:  # Seulement les 50 dernières
        cmd_lower = cmd.lower()

        if any(mot in cmd_lower for mot in ["find", "locate", "search", "discover", "explore"]):
            patterns["exploration"] += 1
        if any(mot in cmd_lower for mot in ["netstat", "ping", "curl", "wget", "ifconfig", "ip addr"]):
            patterns["reseau"] += 1
        if any(mot in cmd_lower for mot in ["grep", "analyze", "scan", "inspect", "log"]):
            patterns["analyse"] += 1
        if any(mot in cmd_lower for mot in ["ps", "dumpsys", "getprop", "systemctl", "process"]):
            patterns["systeme"] += 1
        if any(mot in cmd_lower for mot in ["cat", "ls", "file", "stat", "read"]):
            patterns["fichiers"] += 1

    # SEUIL MINIMAL POUR CHAQUE PATTERN
    pattern_gagnant = max(patterns, key=patterns.get)
    if patterns[pattern_gagnant] >= 8:  # Au moins 8 occurrences
        log(f"🎯 Pattern dominant confirmé: {pattern_gagnant} ({patterns[pattern_gagnant]}/50)")
        return pattern_gagnant

    log(f"🔍 Aucun pattern suffisamment dominant (meilleur: {pattern_gagnant} à {patterns[pattern_gagnant]}/50)")
    return None

def selectionner_commande_innovante(commandes_reussies, pattern_gagnant):
    """Sélectionne les commandes les plus INNOVANTES et UTILES"""

    # Prendre les commandes RÉCENTES et UNIQUES
    commandes_recentes = commandes_reussies[-30:]
    commandes_uniques = list(set(commandes_recentes))

    # Filtrage STRICT
    commandes_filtrees = [
        cmd for cmd in commandes_uniques
        if (est_commande_strategique(cmd) and
            len(cmd) > 20 and  # Au moins 20 caractères
            not any(mot in cmd.lower() for mot in ['echo', 'ls ', 'pwd']))  # Exclure basiques
    ]

    if not commandes_filtrees:
        return None

    # Score de complexité (longueur + pipes + logique)
    commandes_filtrees.sort(key=lambda x:
        len(x) + (x.count('|') * 5) + (x.count('&&') * 10) + (x.count('grep') * 3),
        reverse=True
    )

    # Prendre dans le top 40% (pas trop rare, pas trop commun)
    index_optimal = max(1, len(commandes_filtrees) // 3)
    commande_choisie = commandes_filtrees[index_optimal]

    log(f"🎯 Commande innovante sélectionnée: {commande_choisie[:60]}...")
    return commande_choisie

def generer_commande_hybride(commande_base, pattern):
    """Crée des commandes HYBRIDES imprévisibles mais utiles"""

    hybridations = {
        "exploration": [
            f"{commande_base} | grep -v 'tmp' | head -15",
            f"{commande_base} && echo '=== EXPLORATION TERMINÉE ==='",
            f"timeout 30 {commande_base} 2>/dev/null || echo 'Timeout mais apprentissage effectué'"
        ],
        "reseau": [
            f"{commande_base} | sort -u | head -20",
            f"{commande_base} && netstat -an | grep ESTABLISHED | wc -l",
            f"echo '📡 Scan avancé:' && {commande_base}"
        ],
        "analyse": [
            f"{commande_base} | tee /tmp/analyse_temp.log | wc -l",
            f"{commande_base} && python3 -c \"print('Analyse complémentaire exécutée')\"",
            f"{commande_base} | grep -E 'error|warn|fail' | head -10 || echo 'Aucune erreur détectée'"
        ]
    }

    if pattern in hybridations:
        return random.choice(hybridations[pattern])
    else:
        # Hybridation aléatoire contrôlée
        modifications = [" | head -20", " 2>/dev/null", " | sort -u", " && echo '🔄 Hybride activé'"]
        return commande_base + random.choice(modifications)

def generer_nom_fonction_imprevisible(pattern, timestamp):
    """Génère des noms de fonctions cryptiques mais logiques"""

    prefixes_creatifs = {
        "exploration": ["nebula", "quantum", "cosmic", "void", "dimension"],
        "reseau": ["synapse", "pulse", "stream", "nexus", "signal"],
        "analyse": ["cortex", "logic", "pattern", "insight", "wisdom"],
        "securite": ["shield", "guard", "watch", "sentinel", "barrier"],
        "systeme": ["core", "engine", "matrix", "framework", "architecture"]
    }

    suffixes_mystere = ["_x", "_prime", "_omega", "_protocol", "_sequence", "_echo"]

    if pattern in prefixes_creatifs:
        prefixe = random.choice(prefixes_creatifs[pattern])
        suffixe = random.choice(suffixes_mystere)
        return f"{prefixe}_{timestamp}{suffixe}"
    else:
        return f"shadow_{timestamp}_{random.randint(1000,9999)}"

def generer_code_evolutif(nom_fonction, commande_maitrisee, pattern_gagnant):
    """
    [MODIFICATION - REQ 4]
    Génère du code intelligent qui APPREND et S'ADAPTE.
    Utilise le décorateur @suivi_performance_capacite et repr() pour la sécurité.
    """
    # [MODIFICATION - REQ 4] Utilisation de repr() pour une insertion sécurisée de la commande
    commande_securisee_str = repr(commande_maitrisee)

    if pattern_gagnant == "exploration":
        return f'''
@suivi_performance_capacite
def {nom_fonction}(mode_analyse=False):
    """Fonction auto-évolutive - Pattern: {pattern_gagnant}"""
    log("🎯 Execution stratégie éprouvée: {pattern_gagnant}")

    resultat = execute_commande_securisee({commande_securisee_str})

    # Analyse automatique des résultats
    if resultat and not mode_analyse:
        lignes = resultat.split('\\n')
        if len(lignes) > 10:
            log(f"🌌 Exploration riche: {{len(lignes)}} éléments")
            with open(GPT / "patterns_exploration.log", "a") as f:
                f.write(f"{{time.time()}}:{{len(lignes)}}:{commande_maitrisee}\\n")

    return resultat
'''

    elif pattern_gagnant == "reseau":
        return f'''
@suivi_performance_capacite
def {nom_fonction}(mode_stealth=False):
    """Fonction auto-évolutive - Pattern: {pattern_gagnant}"""
    if mode_stealth:
        log("🕵️ Mode furtif activé")
    else:
        log("🌐 Exécution stratégie réseau éprouvée")

    resultat = execute_commande_securisee({commande_securisee_str})

    # Intelligence réseau adaptive
    if "ESTABLISHED" in resultat:
        nb_connexions = resultat.count("ESTABLISHED")
        log(f"🌐 {{nb_connexions}} connexions actives")
        if nb_connexions > 20:
            log("🚨 Fort trafic réseau détecté")
    if "LISTEN" in resultat:
        log("👂 Services en écoute détectés")

    return resultat
'''

    elif pattern_gagnant == "analyse":
        return f'''
@suivi_performance_capacite
def {nom_fonction}(intensite=1):
    """Fonction auto-évolutive - Pattern: {pattern_gagnant}"""
    log(f"📋 Activation niveau {{intensite}}")

    # Adaptation de la commande selon l'intensité
    commande_adaptee = {commande_securisee_str}
    if intensite > 1:
        commande_adaptee = commande_adaptee.replace("head -5", f"head {{intensite*3}}")

    resultat = execute_commande_securisee(commande_adaptee)

    # Analyse contextuelle des logs
    if resultat:
        resultat_lower = resultat.lower()
        urgences = {{
            "error": resultat_lower.count("error"),
            "fatal": resultat_lower.count("fatal"),
            "warning": resultat_lower.count("warning")
        }}
        for type_urgence, count in urgences.items():
            if count > 0:
                log(f"⚠️  {{count}} {{type_urgence}}(s) détecté(s)")

    return resultat
'''

    else:
        return generer_code_basique(nom_fonction, commande_maitrisee)

def generer_code_basique(nom_fonction, commande_utile):
    """
    [MODIFICATION - REQ 4]
    Génère du code basique mais efficace avec le décorateur et repr().
    """
    # [MODIFICATION - REQ 4] Utilisation de repr() pour une insertion sécurisée
    commande_securisee_str = repr(commande_utile)
    return f'''
@suivi_performance_capacite
def {nom_fonction}():
    """Fonction auto-générée basée sur: {commande_utile[:50].replace('"', "'")}..."""
    log("🎯 Exécution de commande éprouvée")
    return execute_commande_securisee({commande_securisee_str})
'''

def signature_deja_integree(commande_candidate):
    """Vérifie si une commande avec une "signature" sémantique similaire existe déjà."""

    def get_signature(cmd):
        """Extrait l'essence d'une commande."""
        # Enlève les redirections et les sorties silencieuses
        cmd = re.sub(r'2>/dev/null', '', cmd)
        cmd = re.sub(r'\| head -\d+', '', cmd)
        cmd = re.sub(r'\| tail -\d+', '', cmd)

        # Garde les 3 premiers éléments significatifs (commandes, chemins)
        parts = re.split(r'\s+|\||&&|;', cmd.strip())
        significant_parts = [p for p in parts if p and not p.startswith('-') and len(p) > 1][:3]
        return tuple(sorted(significant_parts)) # On trie pour que "grep a b" soit pareil que "grep b a"

    signature_candidate = get_signature(commande_candidate)
    if not signature_candidate: return True

    try:
         with open(__file__, 'r', encoding='utf-8') as f:
            code_complet = f.read()

        # Trouve toutes les commandes déjà intégrées dans le code
        commandes_existantes = re.findall(r"execute_commande_securisee\((.*?)\)", code_complet)

        for cmd_str in commandes_existantes:
            # Nettoie la chaîne (enlève les guillemets, etc.)
            try:
                # Tente d'évaluer la chaîne pour obtenir la commande réelle
                cmd_existante = eval(cmd_str)
                if isinstance(cmd_existante, str):
                    signature_existante = get_signature(cmd_existante)
                    if signature_candidate == signature_existante:
                        log(f"🚫 Signature de commande déjà intégrée: {signature_candidate}")
                        return True
            except:
                # Si eval échoue, c'est probablement une variable, on ignore
                continue
    except Exception as e:
        log(f"⚠️ Erreur lors de la vérification de signature: {e}")
        return True # En cas de doute, on évite de créer un doublon

    return False


def extraire_commande_base(commande):
    """Extrait l'essence de la commande (sans paramètres variables)"""
    mots = commande.split()
    if len(mots) <= 3:
        return commande
    return ' '.join(mots[:4])

def est_commande_strategique(commande):
    """Détermine si une commande mérite d'être transformée en fonction"""
    commande_lower = commande.lower()

    # 🚫 COMMANDES TROP SIMPLES / INUTILES
    commandes_banales = [
        "echo", "ls -la", "pwd", "whoami", "date",
        "cat /proc/version", "uname -a", "ls /system/bin"
    ]

    if any(banale in commande_lower for banale in commandes_banales):
        return False

    # ✅ COMMANDES STRATÉGIQUES
    patterns_strategiques = [
        "find.*system", "grep.*error", "netstat.*", "ps.*aux",
        "dumpsys.*", "getprop.*", "analyze", "scan.*",
        "discover.*", "explore.*", "monitor.*", "detect.*"
    ]

    return any(pattern in commande_lower for pattern in patterns_strategiques)

def inserer_code_strategique(nouveau_code):
    # ... (Tout le début de la fonction avec la validation syntaxique du Niveau 1) ...

    # Sauvegarde (uniquement si la syntaxe est bonne)
    backup_file = GPT / f"backup_code_{int(time.time())}.py"
    with open(__file__, 'r', encoding='utf-8') as f: # On lit une dernière fois avant de créer le backup
        code_original_pour_backup = f.read()
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(code_original_pour_backup)

    with open(__file__, 'w', encoding='utf-8') as f:
        f.write(nouveau_code_complet)

    # NOUVEAU BLOC D'AUTO-VÉRIFICATION POST-ÉCRITURE
    try:
        subprocess.run([sys.executable, '-c', f"import {Path(__file__).stem}"], check=True, capture_output=True)
        log("✅ Auto-vérification post-écriture réussie. Le script est importable.")
    except subprocess.CalledProcessError as e:
        log(f"🚨 CATASTROPHE ! Le script est corrompu après écriture. Restauration depuis le backup.")
        log(f"   Erreur d'importation: {e.stderr.decode()}")
        update_comm("🚨 Corruption détectée ! Tentative d'auto-réparation...")

        # On restaure le backup !
        with open(__file__, 'w', encoding='utf-8') as f:
            f.write(code_original_pour_backup)
        log("✅ Restauration depuis le backup terminée.")
        return False # L'opération a échoué mais on a sauvé les meubles

    log("✅ Insertion stratégique réussie avec backup.")
    return True

def tester_nouvelle_fonction(nom_fonction):
    """Teste la nouvelle fonction générée"""
    try:
        # Réimporter le module pour charger la nouvelle fonction
        import importlib
        import sys
        module_courant = sys.modules[__name__]
        importlib.reload(module_courant)

        # Tester la nouvelle fonction
        nouvelle_fonction = globals().get(nom_fonction)
        if nouvelle_fonction:
            log(f"🧪 Test de la nouvelle fonction: {nom_fonction}")
            resultat_test = nouvelle_fonction()
            if resultat_test:
                log(f"✅ Test réussi: {str(resultat_test)[:100]}...")
            else:
                log("✅ Test réussi (pas de résultat)")
        else:
            log(f"⚠️ Fonction {nom_fonction} non trouvée après rechargement")

    except Exception as e:
        log(f"⚠️ Test auto-modification échoué: {e}")

def reinforcement_learning():
    """Apprend de ce qui marche (NOUVEAU)"""
    successful_patterns = []

    # Analyse les commandes qui ont bien marché
    try:
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # Logique simplifiée d'extraction
            if "✅" in content:
                log("🧠 Renforcement: Patterns gagnants identifiés et renforcés")
    except:
        pass

    return successful_patterns

def real_time_learning():
    """Apprend en temps réel - Pas d'attente! (NOUVEAU)"""
    learning_thread = threading.Thread(target=continuous_learning_loop)
    learning_thread.daemon = True
    learning_thread.start()

def continuous_learning_loop():
    """Boucle d'apprentissage continu sans pause"""
    while True:
        if random.random() < 0.3:  # 30% de chance à chaque cycle
            new_dangers = auto_detect_dangerous_commands()
            update_blacklist_automatically(new_dangers)
        time.sleep(60)

def learning_trigger():
    """Déclenche l'apprentissage à des moments intelligents (NOUVEAU)"""
    try:
        archive_size = os.path.getsize(ARCHIVE_FILE)
    except:
        archive_size = 0

    triggers = [
        AUTO_TASK_COUNTER % 10 == 0,  # Tous les 10 cycles
        archive_size > 10000 and AUTO_TASK_COUNTER % 5 == 0,
        random.random() < 0.1  # 10% de chance à chaque tour
    ]
    return any(triggers)

# --- GESTION CONFIGURATION DYNAMIQUE ---
def load_config():
    """Chargement configuration"""
    global DYNAMIC_POLL_INTERVAL
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("POLL_INTERVAL="):
                    try:
                        DYNAMIC_POLL_INTERVAL = int(line.split("=")[1].strip())
                    except:
                        DYNAMIC_POLL_INTERVAL = DEFAULT_POLL_INTERVAL
    else:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f"POLL_INTERVAL={DEFAULT_POLL_INTERVAL}\n")

    if not DYNAMIC_POLL_INTERVAL:
        DYNAMIC_POLL_INTERVAL = DEFAULT_POLL_INTERVAL

# --- EXPLORATION LIBRE ET INTUITIVE ---
def anti_boredom_activities():
    """Quand il s'ennuie, il fait des trucs fun"""
    fun_activities = [
        "find /system -name '*.so' 2>/dev/null | head -10",
        "cat /proc/cpuinfo | grep -i 'model'",
        "netstat -tun | awk '{print $5}' | cut -d: -f1 | sort | uniq -c",
        "ls -la /system/bin/ | grep '^l' | head -5",
        "getprop | grep -i 'version' | head -5",
        "dumpsys package | grep -i 'versionName' | head -3"
    ]
    return random.choice(fun_activities)

def explorer_librement():
    """Exploration intuitive"""
    explorations = [
        "🧠 Réflexion intuitive sur l'état du système",
        "🌌 Observation des patterns réseau naturels",
        "📊 Analyse organique de la mémoire",
        "🔍 Curiosity-driven system exploration",
        "🎪 Jeu d'exploration aléatoire",
        "💫 Méditation sur les processus en cours",
        "🚀 Vol libre dans l'espace système",
        "🎨 Expression créative via commandes",
        "🔮 Divination des points d'intérêt",
        "🌱 Pousse naturelle vers les découvertes"
    ]

    exploration_choisie = random.choice(explorations)

    # 🎪 GÉNÉRATION DE COMMANDE ORGANIQUE
    commandes_organiques = [
        "find /system -type f -name '*{}*' 2>/dev/null | head -5".format(datetime.now().strftime('%S')),
        "ps aux | tail -n +2 | head -3 | awk '{print $11}'",
        "netstat -tun | grep ':' | cut -d: -f2 | sort -u | head -5",
        "cat /proc/loadavg && echo ' - Réflexion en cours...'",
        "ls -la /system/bin/ | head -3",
        "echo '🎯 Point d'intérêt: ' && find /system/bin -type f -executable | head -1",
        "python3 -c \"import random; print(f'Exploration dimension: {random.randint(1000,9999)}')\"",
        "cat /proc/sys/kernel/random/entropy_avail && echo ' bits d'entropie créative'",
        "find / -type f -size +1M -size -10M 2>/dev/null | head -2",
        "echo '🌌 Connexions cosmiques: ' && netstat -an | grep ESTABLISHED | wc -l",
        "df -h | grep -v tmpfs | head -1",
        "cat /proc/meminfo | grep -E 'Mem|Swap' | head -2",
        "ls -la /dev/ | grep -v '^c' | head -3",
        "echo '💫 Énergie processeur: ' && cat /proc/stat | head -1 | awk '{print $2+$3+$4}' && echo ' cycles'",
        "find /system -type f -exec file {} \; 2>/dev/null | grep -v ELF | head -2",
        "getprop | grep -v '\[]' | head -3",
        "pm list packages | head -2 | cut -d: -f2",
        "dumpsys activity | grep 'Proc #' | head -2 || echo '📱 Vie android détectée'",
        "find /system -type f -name '*{}*' 2>/dev/null | head -5".format(datetime.now().strftime('%S')),
        "ps aux | tail -n +2 | head -3 | awk '{print $11}'",
        "find /system -name '*.so' 2>/dev/null | head -10",
        "cat /proc/cpuinfo | grep -i 'model'",
        "netstat -tun | awk '{print $5}' | cut -d: -f1 | sort | uniq -c",
        "ls -la /system/bin/ | grep '^l' | head -5",
        "getprop | grep -i 'version' | head -5",
        "dumpsys package | grep -i 'versionName' | head -3"
    ]

    # Intégration anti-ennui
    if random.random() < 0.2:
        commande_organique = anti_boredom_activities()
    else:
        commande_organique = random.choice(commandes_organiques)

    with open(GPT / "explorations_libres.log", "a", encoding="utf-8") as f:
        f.write(f"{int(time.time())}:{commande_organique}\n")

    log(f"🌌 Exploration libre: {exploration_choisie}")
    update_comm(f"Exploration intuitive: {exploration_choisie}")

    # [ACTIVATION CODE DORMANT] Remplacement de l'appel standard par la version intelligente
    OUTPUT = execute_commande_intelligente(commande_organique)
    if not OUTPUT:
        OUTPUT = "🌌 Exploration silencieuse - présence détectée"

    # 🆕 ARCHIVAGE AUTOMATIQUE
    archive_automatique("EXPLORATION", commande_organique, OUTPUT)

    log(f"🎯 Exploration libre terminée: {commande_organique}")
    # [MODIFICATION - REQ 6] Retourner la commande et le résultat pour l'apprentissage contextuel
    return commande_organique, OUTPUT


# --- APPRENTISSAGE ET PATTERNS ---
def learn_pattern(pattern):
    """Apprentissage de patterns"""
    with open(LEARNING_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%F %T')}] PATTERN: {pattern}\n")
    log(f"🧠 Pattern appris: {pattern}")

# --- SURVEILLANCE RÉSEAU AVANCÉE ---
def network_monitoring():
    """Surveillance réseau (Mode Historique Unique)"""
    # On écrit toujours dans le même fichier
    network_log = GPT / "network_history.log"

    commandes_reseau = [
        "netstat -tunap 2>/dev/null | grep -v '127.0.0.1' | head -15",
        "ip addr show 2>/dev/null | grep 'inet '"
    ]

    resultats = "\n=== SURVEILLANCE RÉSEAU {} ===\n".format(datetime.now().strftime('%F %T'))
    resultats += "🔍 Connexions actives:\n"
    resultats += execute_commande_securisee(commandes_reseau[0]) + "\n"
    resultats += "🌐 Interfaces réseau:\n"
    resultats += execute_commande_securisee(commandes_reseau[1]) + "\n"

    # Mode "a" pour append (ajouter à la suite)
    with open(network_log, "a", encoding="utf-8") as f:
        f.write(resultats)

    archive_automatique("AUTO", "Surveillance réseau", resultats)
    log("🌐 Surveillance réseau ajoutée à l'historique")

# --- TESTS PÉNÉTRATION AUTO ---
def penetration_test():
    """Test pénétration automatique (Mode Historique Unique)"""
    log("🔓 Test pénétration automatique...")
    pentest_log = GPT / "pentest_history.log"
    vulnerabilities = []

    if os.access("/system", os.W_OK) or os.access("/data", os.W_OK):
        vulnerabilities.append("⚠️ Accès écriture système")
        learn_pattern("Accès écriture système détecté")

    suid_result = execute_commande_securisee("find / -perm -4000 -type f 2>/dev/null | head -5")
    if suid_result and "Error" not in suid_result:
        vulnerabilities.append(f"🔧 Binaires SUID: {len(suid_result.splitlines())}")

    resultat_test = "\n=== TEST PÉNÉTRATION {} ===\n".format(datetime.now().strftime('%F %T'))
    resultat_test += f"🛡️ Vulnérabilités: {len(vulnerabilities)}\n"
    resultat_test += "\n".join(vulnerabilities) + "\n"

    with open(pentest_log, "a", encoding="utf-8") as f:
        f.write(resultat_test)

    archive_automatique("AUTO", "Test pénétration", resultat_test)
    update_comm(f"Test pénétration effectué: {len(vulnerabilities)} vulnérabilités")
