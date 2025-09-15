#!/bin/bash
echo "⚙️ Configuration initiale du système Jules..."

# Créer la structure de répertoires
mkdir -p backups snapshots logs

# Copier le fichier de configuration par défaut
if [ ! -f config.json ]; then
    cat > config.json << EOF
{
  "LOG_FILE": "logs/ai_debug_log.ndjson",
  "CRASH_FILE": "logs/ai_crash_report.zjson",
  "PID_FILE": "logs/ai_debug.pid",
  "SECRETS_SCAN_FILE": "logs/secrets_scan_report.json",
  "DEPENDENCY_AUDIT_FILE": "logs/dependency_audit_report.json",
  "MEMORY_INTEGRATION_FILE": "logs/memory_integration.json",
  "SANDBOX_PATH": "$(pwd)",

  "LOGGING": {
    "LOG_LEVEL": "INFO",
    "MAX_LOG_SIZE_MB": 10,
    "BACKUP_COUNT": 5
  },

  "SECURITY": {
    "ALLOWED_EXTENSIONS": [".py", ".js", ".json", ".txt", ".md", ".sh", ".yml", ".yaml"],
    "SECRET_SCAN_PATTERNS": [
      "[a-zA-Z0-9]{32,}",
      "sk_live_[a-zA-Z0-9]{20,}",
      "AKIA[0-9A-Z]{16}",
      "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
      "-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"
    ]
  },

  "THRESHOLDS": {
    "MEMORY_THRESHOLD": 85,
    "CPU_THRESHOLD": 90,
    "DISK_USAGE_THRESHOLD": 90
  }
}
EOF
    echo "✅ Fichier config.json créé"
else
    echo "✅ Fichier config.json existe déjà"
fi

# Initialiser les bases de données
python3 -c "
from ai_supervisor.db.database import SurveillanceDatabase
import os

dbs = [
    'process_history.db',
    'network_history.db',
    'file_history.db',
    'performance_history.db'
]

for db_file in dbs:
    if not os.path.exists(db_file):
        db = SurveillanceDatabase(db_file)
        db.init_database()
        print(f'✅ Base de données {db_file} initialisée')
    else:
        print(f'✅ Base de données {db_file} existe déjà')
"

echo "✅ Configuration terminée!"
