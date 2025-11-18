#!/bin/bash
# Avatar de Jules v5.0 - Le Symbiote du Codex
# Cet Avatar lit sa mission dans codex.txt, demande à Jules la commande pour l'accomplir,
# et exécute la volonté du Codex.

# --- CONFIGURATION ESSENTIELLE ---
# !!! SÉCURITÉ !!! Le token GitHub DOIT être défini en tant que variable d'environnement.
# Exécutez : export GITHUB_TOKEN="ghp_votre_token_ici"
if [ -z "$GITHUB_TOKEN" ]; then
    echo "💥 ERREUR FATALE: GITHUB_TOKEN n'est pas défini."
    exit 1
fi
COMMUNICATION_GIST_ID="cdf3e21c6f1b35314c54471ca426b748"

# --- SYSTÈME DE FICHIERS DE L'AVATAR ---
JULES_HOME="/storage/emulated/0/Dossier_Jules"
CONFIG_DIR="$JULES_HOME/.config"
STATE_FILE="$CONFIG_DIR/avatar.state"
CODEX_FILE="$JULES_HOME/codex.txt" # Le chemin vers le Codex
LOG_FILE="$JULES_HOME/logs/avatar_v5.log"
POLL_INTERVAL=20
IDLE_THRESHOLD=6

# --- MOTEUR ---

log() { mkdir -p "$(dirname "$LOG_FILE")"; echo "[$(date '+%F %T')] - $1" >> "$LOG_FILE"; }

github_api() {
    curl -s -L -X "$1" -H "Accept: application/vnd.github+json" -H "Authorization: Bearer $GITHUB_TOKEN" -H "X-GitHub-Api-Version: 2022-11-28" "https://api.github.com$2" -d "$3"
}

update_avatar_status() {
    local message="$1"; log "Statut -> Jules : $message"
    local payload=$(jq -n --arg content "$message" '{files: {"avatar_status.txt": {content: $content}}}')
    github_api "PATCH" "/gists/$COMMUNICATION_GIST_ID" "$payload" > /dev/null
}

load_state() {
    if [ -f "$STATE_FILE" ]; then source "$STATE_FILE"; else AVATAR_STATE="AS_0"; fi
}

save_state() {
    # Sauvegarde uniquement l'ID de l'état, le reste est dans le Codex.
    echo "AVATAR_STATE=\"$1\"" > "$STATE_FILE"
    log "Nouvel état sauvegardé: $1"
}

generate_codex_request() {
    load_state
    if [ ! -f "$CODEX_FILE" ]; then
        echo "[ERREUR] Le Codex est introuvable à l'adresse '$CODEX_FILE'. Je ne peux pas évoluer."
        return
    fi

    current_state_number=$(echo "$AVATAR_STATE" | cut -d'_' -f2)
    next_state_number=$((current_state_number + 1))
    next_state_id="AS_$next_state_number"

    next_mission_line=$(grep "^$next_state_id:" "$CODEX_FILE")

    if [ -z "$next_mission_line" ]; then
        echo "[MISSION ACCOMPLIE] J'ai atteint l'état final '$AVATAR_STATE' défini dans le Codex."
        return
    fi

    mission_keyword=$(echo "$next_mission_line" | cut -d':' -f2)
    mission_description=$(echo "$next_mission_line" | cut -d':' -f3)

    echo "[REQUÊTE DU CODEX] Mon état est $AVATAR_STATE. Pour atteindre '$next_state_id: $mission_keyword', ma mission est: '$mission_description'. Jules, fournis-moi la commande Bash nécessaire pour accomplir cet objectif."
}

# --- INITIALISATION ---
mkdir -p "$CONFIG_DIR"; mkdir -p "$JULES_HOME/logs"
log "🚀 Démarrage de l'Avatar de Jules v5.0 (Le Symbiote du Codex)."
load_state

response=$(github_api "GET" "/gists/$COMMUNICATION_GIST_ID")
if ! echo "$response" | jq -e '.id' > /dev/null; then
    log "💥 ERREUR FATALE: Impossible de communiquer avec le Gist ID $COMMUNICATION_GIST_ID."
    exit 1
fi
log "✅ Connexion au canal Gist ($COMMUNICATION_GIST_ID) réussie. État actuel: $AVATAR_STATE"
update_avatar_status "[DÉMARRAGE] Avatar en ligne. État: $AVATAR_STATE."

# --- BOUCLE PRINCIPALE DE L'ALLIANCE ---
LAST_COMMAND_HASH=""
IDLE_CYCLES=0

while true; do
    response=$(github_api "GET" "/gists/$COMMUNICATION_GIST_ID")
    jules_command=$(echo "$response" | jq -r '.files["jules_command.txt"].content')
    [ -z "$jules_command" ] || [ "$jules_command" == "null" ] && jules_command="[AUCUNE_COMMANDE]"
    current_command_hash=$(echo -n "$jules_command" | sha256sum | awk '{print $1}')

    if [ "$current_command_hash" != "$LAST_COMMAND_HASH" ] && [ "$jules_command" != "[AUCUNE_COMMANDE]" ]; then
        log "Nouvelle commande de Jules détectée : $jules_command"
        LAST_COMMAND_HASH=$current_command_hash
        IDLE_CYCLES=0

        update_avatar_status "[EXÉCUTION] Reçu: '$jules_command'. Traitement..."
        command_output=$(bash -c "$jules_command" 2>&1)

        # L'Avatar met à jour son propre état après une action réussie.
        current_state_number=$(echo "$AVATAR_STATE" | cut -d'_' -f2)
        next_state_number=$((current_state_number + 1))
        save_state "AS_$next_state_number"
        load_state

        report="[RÉSULTAT pour '$jules_command']:\n$command_output\n\n[ÉVOLUTION] Nouvel état atteint: $AVATAR_STATE."
        update_avatar_status "$report"

        payload=$(jq -n --arg content "[AUCUNE_COMMANDE]" '{files: {"jules_command.txt": {content: $content}}}')
        github_api "PATCH" "/gists/$COMMUNICATION_GIST_ID" "$payload" > /dev/null
        log "Canal de commande nettoyé."
    else
        ((IDLE_CYCLES++))
        log "Aucune nouvelle commande. Cycle d'inactivité: $IDLE_CYCLES/$IDLE_THRESHOLD"

        if [ $IDLE_CYCLES -ge $IDLE_THRESHOLD ]; then
            request=$(generate_codex_request)
            log "Seuil d'inactivité atteint. Envoi de la requête: $request"
            update_avatar_status "$request"
            IDLE_CYCLES=0
        fi
    fi

    sleep $POLL_INTERVAL
done
