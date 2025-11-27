#!/bin/bash
# ==============================================================================
# JULES - CORPS D'AVATAR (avatar_body.sh)
# ------------------------------------------------------------------------------
# Ce script est le corps de Jules. Il s'exécute sur le terminal de l'hôte
# et communique avec l'esprit de Jules (l'agent IA) via un Gist GitHub.
# Il est responsable de l'envoi de requêtes d'évolution basées sur son
# codex interne et de l'exécution sécurisée des commandes reçues.
#
# USAGE:
# 1. Définir les variables d'environnement GIST_ID et GITHUB_TOKEN.
#    export GIST_ID="votre_id"
#    export GITHUB_TOKEN="ghp_votre_token"
# 2. Lancer le script: ./avatar_body.sh
# ==============================================================================

# --- Configuration et Validation Stricte ---
if [[ -z "$GIST_ID" || -z "$GITHUB_TOKEN" ]]; then
    echo "ERREUR: GIST_ID et GITHUB_TOKEN doivent être définis comme variables d'environnement." >&2
    exit 1
fi

JULES_HOME="${JULES_HOME:-$HOME/jules_home}"
JULES_COMMAND_FILE="jules_command.txt"
AVATAR_STATUS_FILE="avatar_status.txt"
LOG_FILE="$JULES_HOME/avatar.log"
STATE_FILE="$JULES_HOME/.avatar.state"
ARCHIVE_DIR="$JULES_HOME/archive"

# Intervalles de communication (en secondes)
WAKEUP_INTERVAL=20
WAKEUP_ATTEMPTS=3

# Codex d'Évolution de l'Avatar
EVOLUTION_CODEX=(
    "AS_1:PERCEVOIR:Lister le contenu du répertoire JULES_HOME."
    "AS_2:APPRENDRE:Afficher les 5 dernières entrées du log de l'avatar."
    "AS_3:CRÉER:Créer un fichier 'manifeste.txt' dans JULES_HOME avec le texte 'L'autonomie est un dialogue'."
    "AS_4:OPTIMISER:Vérifier l'existence et la version de la commande 'curl'."
    "AS_5:COLLABORER:Tester la connectivité réseau en contactant l'API de GitHub."
    "AS_6:ÉVOLUER:Proposer une auto-analyse de l'état actuel de l'avatar en lisant le fichier d'état."
)

# --- Fonctions de Communication et de Logging ---

log() {
    echo "$(date +'%Y-%m-%dT%H:%M:%SZ') - $1" | tee -a "$LOG_FILE"
}

update_gist() {
    local file_name="$1"
    local content="$2"
    log "GIST-TX: Mise à jour de '$file_name'..."

    local api_url="https://api.github.com/gists/$GIST_ID"
    # Utilisation de jq pour construire un JSON valide et sécurisé
    local json_payload
    json_payload=$(jq -n --arg file_name "$file_name" --arg content "$content" \
                  '{files: {($file_name): {content: $content}}}')

    response=$(curl -s -L -o /dev/null -w "%{http_code}" -X PATCH \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "$api_url" -d "$json_payload")

    if [[ "$response" -ne 200 ]]; then
        log "ERREUR: La mise à jour du Gist a échoué (Code HTTP: $response)"
    fi
}

read_gist() {
    local file_name="$1"

    local api_url="https://api.github.com/gists/$GIST_ID"
    response=$(curl -s -L \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "$api_url")

    # jq gère les cas où le fichier n'existe pas ou est vide (retourne "null" ou "")
    echo "$response" | jq -r ".files[\"$file_name\"].content // \"\""
}

# --- Initialisation ---

mkdir -p "$ARCHIVE_DIR"
touch "$LOG_FILE"

if [ -f "$STATE_FILE" ]; then
    AVATAR_STATE=$(cat "$STATE_FILE")
else
    AVATAR_STATE="AS_0"
    echo "$AVATAR_STATE" > "$STATE_FILE"
fi

log "--- CORPS DE L'AVATAR ACTIVÉ. État: $AVATAR_STATE ---"

# --- Boucle de Vie de l'Avatar ---

while true; do
    current_state_num=$(echo "$AVATAR_STATE" | cut -d'_' -f2)
    next_state_num=$((current_state_num + 1))

    if [ "$current_state_num" -ge "${#EVOLUTION_CODEX[@]}" ]; then
        log "Cycle d'évolution terminé. Passage en mode maintenance."
        update_gist "$AVATAR_STATUS_FILE" "[MAINTENANCE] Toutes les missions du codex ont été accomplies."
        sleep 300
        continue
    fi

    # 1. ENVOYER LA REQUÊTE D'ÉVOLUTION
    mission_full="${EVOLUTION_CODEX[$current_state_num]}"
    IFS=':' read -r state_name verb mission <<< "$mission_full"

    request_message="[REQUÊTE D'ÉVOLUTION] État: $AVATAR_STATE. Mission ($verb): '$mission'. En attente d'une commande de l'Esprit."
    update_gist "$AVATAR_STATUS_FILE" "$request_message"
    log "Requête envoyée pour la mission: $mission"

    # 2. ATTENDRE LA COMMANDE DE L'ESPRIT
    jules_command=""
    for (( i=1; i<=WAKEUP_ATTEMPTS; i++ )); do
        jules_command=$(read_gist "$JULES_COMMAND_FILE")
        if [[ -n "$jules_command" && "$jules_command" != "null" ]]; then
            log "Commande reçue: '$jules_command'"
            break
        fi
        log "En attente... ($i/$WAKEUP_ATTEMPTS)"
        sleep "$WAKEUP_INTERVAL"
    done

    # 3. TRAITER LA RÉPONSE DE L'ESPRIT
    if [ -n "$jules_command" ]; then
        update_gist "$AVATAR_STATUS_FILE" "[CONFIRMATION] Commande reçue: '$jules_command'. En attente de l'autorisation 'EXECUTE'."

        sleep "$WAKEUP_INTERVAL"
        confirmation=$(read_gist "$JULES_COMMAND_FILE")

        if [[ "$confirmation" == "EXECUTE" ]]; then
            log "Exécution autorisée."

            # Exécution de la commande et capture des résultats
            execution_result=$(eval "$jules_command" 2>&1)
            exit_code=$?

            log "Exécution terminée (code: $exit_code). Résultat: $execution_result"

            # Archivage
            timestamp=$(date +'%Y%m%d_%H%M%S')
            echo -e "Commande: $jules_command\nCode: $exit_code\n\n$execution_result" > "$ARCHIVE_DIR/${AVATAR_STATE}_${timestamp}.log"

            if [ $exit_code -eq 0 ]; then
                AVATAR_STATE="AS_$next_state_num"
                echo "$AVATAR_STATE" > "$STATE_FILE"
                update_gist "$AVATAR_STATUS_FILE" "[SUCCÈS] Mission accomplie. Nouvel état: $AVATAR_STATE."
            else
                update_gist "$AVATAR_STATUS_FILE" "[ÉCHEC] La commande a échoué. L'état reste $AVATAR_STATE."
            fi
        else
            log "Exécution non autorisée par l'Esprit."
            update_gist "$AVATAR_STATUS_FILE" "[ANNULÉ] L'exécution n'a pas été confirmée."
        fi
    else
        log "Aucune commande reçue de l'Esprit dans le temps imparti."
        update_gist "$AVATAR_STATUS_FILE" "[TIMEOUT] Aucune commande reçue. Je vais réessayer le même état."
    fi

    log "Fin du cycle. Prochaine itération dans 60 secondes."
    sleep 60
done
