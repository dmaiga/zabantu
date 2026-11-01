# Fonctions communes aux scripts de sauvegarde (à charger avec « source », pas à lancer).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
# Hors de public_html : une sauvegarde ne doit jamais être téléchargeable depuis le web.
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/zabantu}"
KEEP_DAYS="${KEEP_DAYS:-14}"

umask 077   # sauvegardes lisibles par le seul propriétaire

log() { echo "$(date '+%F %T') $*"; }
fail() { log "ERREUR : $*" >&2; exit 1; }

# Lit une clé du .env sans exécuter le fichier (dernière occurrence, guillemets retirés).
env_get() {
  [ -f "$ENV_FILE" ] || fail "fichier .env introuvable : $ENV_FILE"
  local value
  value=$(grep -E "^[[:space:]]*$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | tr -d '\r')
  value="${value%\"}"; value="${value#\"}"; value="${value%\'}"; value="${value#\'}"
  printf '%s' "$value"
}

# Supprime les sauvegardes plus anciennes que KEEP_DAYS jours : prefix_pattern, par exemple « zabantu_db_*.dump ».
prune() {
  find "$BACKUP_DIR" -maxdepth 1 -type f -name "$1" -mtime "+$KEEP_DAYS" -print -delete |
    while read -r old; do log "supprimée (plus de $KEEP_DAYS jours) : $old"; done
}
