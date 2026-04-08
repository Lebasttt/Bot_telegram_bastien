FONCTIONS DE BASE (journalisation, communication, archivage)

log

· structlog : logs structurés JSON
· rich : affichage coloré console
· logging + RotatingFileHandler : rotation fichiers logs
· inspect : nom fonction appelante
· traceback : stack trace erreurs
· orjson / ujson (opt) : parsing JSON ultra-rapide

update_comm

· textblob : analyse sentiment
· vaderSentiment : analyse émotion sociale
· emoji : détection émoticônes
· pygments : coloration syntaxique
· pandas : DataFrames historique
· sqlite3 : persistance conversations

archive_automatique

· sqlite3 : stockage relationnel
· pandas + numpy : statistiques archives
· dill : sérialisation objets complexes
· json : format structuré
· gzip : compression
· orjson (opt) : encodage JSON rapide

ecrire_ligne_unique

· bloom_filter : vérification mémoire O(1)
· sqlite3 : persistance signatures
· hashlib : hachage SHA‑256
· threading.Lock : verrou thread-safe
· mmap : lecture rapide gros fichiers

---

SÉCURITÉ ET EXÉCUTION DES COMMANDES

execute_commande_securisee

· subprocess : exécution native
· psutil : CPU/mémoire avant/après
· resource : limitation ressources
· tracemalloc : détection fuites mémoire
· secrets : tokens temporaires
· asyncio + timeout : exécution non‑bloquante
· shlex.quote() : échappement arguments
· tempfile : fichiers temporaires
· cryptography.fernet : chiffrement commandes sensibles
· signal : gestion SIGINT/SIGTERM
· pty : pseudo‑terminaux
· select : surveillance I/O
· threading / concurrent.futures : parallélisation
· queue.Queue : file attente
· filelock : verrou fichiers
· tenacity : retry intelligent
· httpx (opt) : requêtes async modernes

detect_sabotage_attempt

· ast : analyse arbre syntaxique
· tokenize : tokenisation
· bandit : scanner sécurité
· pyyaml : règles externes
· re : patterns regex

extract_file_path_from_error

· re : extraction regex
