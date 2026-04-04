from utils import *
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
        knowledge_dir = JULES_HOME / "web_knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)

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
        self.fichier_historique = JULES_HOME / "historique_urls.json"
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

# 🔥 SYSTÈME COMPLET D'APPRENTISSAGE AVANCÉ (version optimisée)
