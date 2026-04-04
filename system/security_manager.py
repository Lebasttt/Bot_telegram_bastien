from utils import *
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
    # Essayer d'abord le parseur XML si lxml est installé, sinon HTML
    soup = None
    try:
        # Tentative avec XML (plus fiable pour les documents XML/HTML bien formés)
        soup = BeautifulSoup(html, 'xml')
    except Exception:
        # Fallback sur html.parser (moins strict)
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
    log(f"?? ACTIVATION MODE ULTIME POUR: {url}")

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
