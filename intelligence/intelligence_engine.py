from utils import *
class GeminiBooster:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "PLACEHOLDER_GEMINI_KEY")
        self.model = "models/gemini-2.0-flash"
        self.last_call = 0
        self.min_interval = 3
        self.discussion_file = JULES_HOME / "discussion.txt"
        self.dashboard_file = JULES_HOME / "gemini_mind.txt"
        self.commands_file = JULES_HOME / "commands.txt"
        self.commands_dir = JULES_HOME / "commande"
        self.last_results_file = JULES_HOME / "last_execution_results.log"
        try:
            JULES_HOME.mkdir(parents=True, exist_ok=True)
            self.commands_dir.mkdir(parents=True, exist_ok=True)
            if not self.dashboard_file.exists():
                self.dashboard_file.write_text("=== DASHBOARD ===\nSTADE: 1\nOBJ: Evolution.", encoding="utf-8")
        except: pass

    def _call_gemini(self, prompt):
        now = time.time()
        if now - self.last_call < self.min_interval:
            time.sleep(max(0.1, self.min_interval - (now - self.last_call)))
        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model}:generateContent?key={self.api_key}"
        sys_p = "=== IDENTITÉ ===\nArchitecte. Travaille SEUL. Utilise /storage/emulated/0/Super_Lab (ABSOLU).\n=== BALISES ===\n- [EXECUTE] cmd [/EXECUTE]\n- [LIRE] path [/LIRE]\n- [ECRIRE] path | ctn [/ECRIRE]\n- [DASHBOARD] notes [/DASHBOARD]"
        data = {"contents": [{"parts": [{"text": f"{sys_p}\n\n{prompt}"}]}]}
        try:
            resp = requests.post(url, headers={'Content-Type': 'application/json'}, json=data, timeout=30)
            self.last_call = time.time()
            if resp.status_code == 200: return resp.json()['candidates'][0]['content']['parts'][0]['text']
            elif resp.status_code == 429: log("⚠️ 429"); self.min_interval = min(60, self.min_interval + 3)
        except: pass
        return None

    def executer_commandes(self):
        any_done = False
        if self.commands_dir.exists():
            for f in self.commands_dir.glob("*"):
                if f.is_file():
                    try:
                        if self._traiter(f.read_text(encoding='utf-8')): any_done = True
                        f.unlink()
                    except: pass
        if self.commands_file.exists():
            try:
                ctn = self.commands_file.read_text(encoding='utf-8')
                if ctn.strip() and self._traiter(ctn): any_done = True
                self.commands_file.write_text("", encoding='utf-8')
            except: pass
        return any_done

    def _traiter(self, contenu):
        action = False
        res_list = []
        for cmd in re.findall(r'\[EXECUTE\](.*?)(?:\[/EXECUTE\]|$)', contenu, re.DOTALL):
            cmd = cmd.strip()
            if not cmd or "bash" in cmd.lower()[:5]: continue
            log(f"🤖 IA EXEC: '{cmd}'")
            out = execute_commande_securisee(cmd)
            res_list.append(f"ORDRE: {cmd}\nRES:\n{out[:2000]}\n---")
            action = True
        for path_str in re.findall(r'\[LIRE\](.*?)(?:\[/LIRE\]|$)', contenu, re.DOTALL):
            p = Path(path_str.strip())
            if not p.is_absolute(): p = JULES_HOME / p
            if p.exists():
                try: res_list.append(f"LECTURE: {p.name}\nCTN:\n{p.read_text(encoding='utf-8')[:3000]}\n---"); action = True
                except: pass
        for m in re.findall(r'\[ECRIRE\](.*?)\|(.*?)(?:\[/ECRIRE\]|$)', contenu, re.DOTALL):
            try:
                nom, ctn = m[0].strip(), m[1].strip()
                p = Path(nom) if Path(nom).is_absolute() else JULES_HOME / nom
                p.parent.mkdir(parents=True, exist_ok=True); p.write_text(ctn, encoding='utf-8')
                res_list.append(f"ECRITURE: {nom} OK\n---"); action = True
            except: pass
        dash = re.search(r'\[DASHBOARD\](.*?)(\[/DASHBOARD\]|$)', contenu, re.DOTALL)
        if dash:
            try: self.dashboard_file.write_text(dash.group(1).strip(), encoding="utf-8"); log("🧠 Dashboard à jour"); action = True
            except: pass
        if res_list:
            try:
                with open(self.last_results_file, "a", encoding="utf-8") as f: f.write("\n".join(res_list) + "\n")
            except: pass
        return action

    def cycle_autonomie(self):
        if time.time() - self.last_call < self.min_interval: return
        log("🧠 Gemini réfléchit...")
        mem = self.dashboard_file.read_text(encoding="utf-8") if self.dashboard_file.exists() else "Init"
        res = ""
        if self.last_results_file.exists():
            try: res = self.last_results_file.read_text(encoding="utf-8"); self.last_results_file.write_text("", encoding="utf-8")
            except: pass
        prompt = f"=== DASHBOARD ===\n{mem}\n\n=== RESULTATS ===\n{res if res else 'Néant'}\n\nAction ?"
        rep = self._call_gemini(prompt)
        if rep: self._traiter(rep)

    def gerer_discussion(self):
        if not self.discussion_file.exists(): return False
        if time.time() - self.last_call < self.min_interval: return False
        try:
            txt = self.discussion_file.read_text(encoding='utf-8')
            lignes = txt.splitlines()
            idx = -1
            for i in range(len(lignes)-1, -1, -1):
                if ("HUMAIN" in lignes[i].upper() or "USER" in lignes[i].upper()) and "[TRAITÉ]" not in lignes[i]:
                    idx = i; break
            if idx != -1:
                msg = lignes[idx]
                log(f"🧠 Discussion: {msg[:50]}...")
                mem = self.dashboard_file.read_text(encoding="utf-8") if self.dashboard_file.exists() else ""
                prompt = f"DASHBOARD: {mem}\n\nMESSAGE HUMAIN: {msg}\n\nRéponse (texte clair) :"
                rep = self._call_gemini(prompt)
                if rep:
                    lignes[idx] += " [TRAITÉ]"
                    clean_rep = re.sub(r'\[.*?\]', '', rep, flags=re.DOTALL).strip()
                    self.discussion_file.write_text("\n".join(lignes) + f"\n\nGEMINI: {clean_rep}\n", encoding='utf-8')
                    self._traiter(rep)
                    return True
        except: pass
        return False

cerveau_gemini = GeminiBooster()

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
    copy_path = JULES_HOME / "copies" / os.path.basename(blocked_file)

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
    learning_file = JULES_HOME / "permission_solutions.log"
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
