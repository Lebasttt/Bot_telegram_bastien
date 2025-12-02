# -*- coding: utf-8 -*-
"""
Module de recherche web avancé.
Contient les outils permettant à l'agent de chercher de l'information sur internet.
"""

import hashlib
import json
import random
import re
import threading
import time
from urllib.parse import quote_plus, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from typing import Callable

from . import config

# Verrou pour s'assurer qu'une seule recherche web a lieu à la fois.
WEB_RESEARCH_LOCK = threading.Lock()

# ==============================================================================
# SECTION 1 : LE SCRAPER "TERMINATOR"
# ==============================================================================

def scrape_terminator_ultime(url: str, log: Callable[[str], None]) -> str | None:
    """
    Scraper avancé conçu pour contourner les protections et extraire le contenu textuel.
    """
    log(f"🦾 LANCEMENT TERMINATOR SUR: {url}")

    session = requests.Session()

    identities = [
        {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'accept-language': 'fr-FR,fr;q=0.9,en;q=0.8'},
        {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'accept-language': 'en-US,en;q=0.5'},
        {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0', 'accept-language': 'fr,fr-FR;q=0.8,en-US;q=0.5'},
        {'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'},
        {'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
    ]

    for attempt in range(3):
        identity = random.choice(identities)
        time.sleep(random.uniform(1, 4))

        try:
            response = session.get(url, headers=identity, timeout=15, allow_redirects=True)

            if response.status_code == 200:
                return _process_content_terminator(response.text, log)
            elif response.status_code in [403, 429]: # Forbidden or Too Many Requests
                log(f"🚫 Accès refusé ({response.status_code}) - Changement d'identité...")
                time.sleep(10)
                continue
            else:
                log(f"⚠️ Code {response.status_code} reçu - Nouvelle tentative...")

        except requests.exceptions.RequestException as e:
            log(f"❌ Erreur réseau lors du scraping: {e}")

    log(f"❌ Échec final du scraping pour {url} après plusieurs tentatives.")
    return None

def _process_content_terminator(html: str, log: Callable[[str], None]) -> str:
    """Nettoie le HTML pour extraire uniquement le texte pertinent."""
    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button']):
        tag.decompose()

    text = soup.get_text(separator='\n', strip=True)

    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if len(line.split()) >= 5: # Garde les lignes avec au moins 5 mots
            lines.append(line)

    final_text = '\n'.join(lines[:40]) # Limite à 40 lignes pertinentes

    log(f"✅ TERMINATOR SUCCÈS: {len(final_text)} caractères extraits")
    return final_text

# ==============================================================================
# SECTION 2 : GESTION DES DOUBLONS
# ==============================================================================

class DeduplicateurUrls:
    """Système pour éviter de visiter plusieurs fois les mêmes URLs ou de traiter du contenu similaire."""
    def __init__(self, log_func: Callable[[str], None]):
        self.log = log_func
        self.urls_visitees = set()
        self.signatures_contenu = set()
        self.history_file = config.get_url_history_file()
        self.charger_historique()

    def charger_historique(self):
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.urls_visitees = set(data.get('urls', []))
                    self.signatures_contenu = set(data.get('signatures', []))
                self.log(f"📚 Historique URLs chargé: {len(self.urls_visitees)} URLs.")
        except (json.JSONDecodeError, IOError) as e:
            self.log(f"⚠️ Impossible de charger l'historique des URLs: {e}")

    def sauvegarder_historique(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({'urls': list(self.urls_visitees), 'signatures': list(self.signatures_contenu)}, f)
        except IOError as e:
            self.log(f"❌ Erreur de sauvegarde de l'historique des URLs: {e}")

    def _nettoyer_url(self, url):
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    def _creer_signature_contenu(self, contenu):
        sample = contenu[:500] + contenu[-500:] if len(contenu) > 1000 else contenu
        return hashlib.md5(f"{len(contenu)}:{sample}".encode('utf-8')).hexdigest()

    def deja_traite(self, url, contenu):
        url_clean = self._nettoyer_url(url)
        signature = self._creer_signature_contenu(contenu)

        if url_clean in self.urls_visitees or signature in self.signatures_contenu:
            return True
        return False

    def enregistrer_visite(self, url, contenu):
        self.urls_visitees.add(self._nettoyer_url(url))
        self.signatures_contenu.add(self._creer_signature_contenu(contenu))
        self.sauvegarder_historique()

# ==============================================================================
# SECTION 3 : FONCTION DE RECHERCHE PRINCIPALE
# ==============================================================================

def web_research(topic: str, log: Callable[[str], None]) -> dict:
    """
    Lance une recherche web sur un sujet donné, en utilisant plusieurs sources
    et en filtrant les résultats pour ne garder que le plus pertinent.
    """
    if not WEB_RESEARCH_LOCK.acquire(blocking=False):
        log("🚦 Recherche web déjà en cours, cycle ignoré.")
        return {}

    log(f"🛰️ [VERROU ACQUIS] Lancement recherche web: {topic}")

    try:
        topic_encoded = quote_plus(topic)

        # --- ÉLARGISSEMENT DES SOURCES ET MOTS-CLÉS ---
        sources = {
            # Sources Généralistes et Techniques
            "Google_Search": f"https://www.google.com/search?q={topic_encoded}",
            "DuckDuckGo_Search": f"https://html.duckduckgo.com/html/?q={topic_encoded}",
            "Wikipedia_Search": f"https://en.wikipedia.org/w/index.php?search={topic_encoded}",
            "StackOverflow": f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q={topic_encoded}&site=stackoverflow",
            "GitHub_API": f"https://api.github.com/search/code?q={topic_encoded}+in:file",
            "Reddit_API": f"https://www.reddit.com/search.json?q={topic_encoded}",

            # Sources Sécurité & Hacking
            "NIST_CVE": f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={topic_encoded}",
            "ExploitDB": f"https://www.exploit-db.com/search?q={topic_encoded}",
            "HackerNews_RSS": "https://feeds.feedburner.com/TheHackerNews",

            # Sources IA & Auto-amélioration
            "ArXiv_AI": f"https://arxiv.org/search/?query={topic_encoded}&searchtype=all&source=header",
            "PapersWithCode": f"https://paperswithcode.com/search?q={topic_encoded}",
        }

        mots_cles_cibles = [
            "android", "termux", "linux", "kernel", "root", "adb", "exploit", "vulnerability",
            "payload", "shellcode", "reverse shell", "cve", "backdoor", "malware", "bypass",
            "privilege escalation", "rce", "injection", "wifi", "packet sniffing", "encryption",
            "python", "bash", "script", "api", "forensic", "hook", "custom rom", "magisk",
            "frida", "metasploit", "apk decompilation", "mobile security", "reverse engineering",
            "ai code generation", "self modifying code", "genetic algorithm", "machine learning",
            "python performance", "reinforcement learning", "automated testing", "code analysis",
            "neural network", "deep learning", "automated programming", "meta learning", "how to",
            "tutorial", "guide", "documentation", "example", "best practice", "solution"
        ]

        mots_cles_poubelle = ["login", "subscribe", "newsletter", "cookie", "consent", "advertisement"]

        deduplicateur = DeduplicateurUrls(log)
        results = {}

        sources_melangees = list(sources.items())
        random.shuffle(sources_melangees)

        for site, url in sources_melangees[:5]: # Limite à 5 sources par recherche pour la vitesse
            try:
                log(f"🌐 Tentative d'accès à {site}...")
                content = scrape_terminator_ultime(url, log)

                if content and not deduplicateur.deja_traite(url, content):
                    deduplicateur.enregistrer_visite(url, content)
                    content_lower = content.lower()

                    if any(trash in content_lower for trash in mots_cles_poubelle):
                        log(f"🗑️ {site}: Rejeté (Contient un mot-clé poubelle)")
                        continue

                    mots_trouves = [mot for mot in mots_cles_cibles if mot in content_lower]
                    if mots_trouves:
                        log(f"💎 PÉPITE ({', '.join(mots_trouves)}): Information pertinente trouvée sur {site}")
                        results[site] = content
                    else:
                        log(f" Aucun mot-clé pertinent trouvé {site}")

            except Exception as e:
                log(f"❌ Erreur majeure pour {site}: {e}")

            time.sleep(random.uniform(2, 5)) # Pause entre les requêtes

        return results

    finally:
        WEB_RESEARCH_LOCK.release()
        log("🛰️ [VERROU RELÂCHÉ] Fin de la recherche web.")
