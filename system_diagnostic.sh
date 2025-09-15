#!/bin/bash
echo "📋 Diagnostic système complet..."

python3 -c "
from ai_supervisor.utils.helpers import get_system_info
import json

info = get_system_info()
print('=== SYSTÈME ===')
print(f'Platforme: {info[\"platform\"][\"system\"]}')
print(f'Python: {info[\"platform\"][\"python_version\"]}')
print(f'Hostname: {info[\"platform\"][\"hostname\"]}')

print('\n=== RESSOURCES ===')
print(f'CPU: {info[\"cpu\"][\"current_percent_usage\"]}% utilisé')
print(f'Mémoire: {info[\"memory\"][\"percent_used\"]}% utilisé')
print(f'Disque: {info[\"disk\"][\"partitions\"][0][\"mountpoint\"] if info[\"disk\"][\"partitions\"] else \"N/A\"}')

print('\n=== JULES ===')
try:
    from ai_supervisor.core.config import CONFIG
    print(f'Sandbox: {CONFIG.get(\"SANDBOX_PATH\", \"N/A\")}')
    print(f'Log: {CONFIG.get(\"LOG_FILE\", \"N/A\")}')
except Exception as e:
    print(f'Erreur config: {e}')
"
