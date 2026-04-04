from config import *
def log(message):
    """Journalisation sécurisée"""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%F %T')}] {message}\n")
    except:
        pass

def update_comm(message):
    """Communication sécurisée"""
    try:
        COMM_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COMM_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%F %T')}] - [Évolution]: {message}\n")
        log(f"📢 Communication: {message}")
    except:
        pass

def archive_automatique(origine, commande, resultat):
    """Archivage automatique complet"""
    timestamp = datetime.now().strftime('%F %T')
    try:
        ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
            f.write(f"=== ARCHIVE [{timestamp}] ===\n")
            f.write(f"ORIGINE: {origine}\n")
            f.write(f"COMMANDE: {commande}\n")
            f.write(f"RESULTAT:\n{resultat}\n")
            f.write("=== FIN ARCHIVE ===\n\n")
        log(f"💾 Archivé automatiquement: {commande}")
    except:
        pass

# ==============================================================================
# LE CERVEAU GEMINI v3.0 (FUSION COMPLÈTE - MODE SOUVERAINETÉ & AUTONOMIE TOTALE)
# ==============================================================================
