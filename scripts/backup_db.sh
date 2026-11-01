#!/usr/bin/env bash
# Sauvegarde de la base PostgreSQL de Zabantu (format compressé, restaurable avec pg_restore).
#
# Usage :   ./scripts/backup_db.sh
# Réglages optionnels (variables d'environnement) :
#   BACKUP_DIR  dossier des sauvegardes     (défaut : ~/backups/zabantu, hors de public_html)
#   KEEP_DAYS   durée de conservation, jours (défaut : 14)
#   ENV_FILE    fichier .env à lire          (défaut : .env à la racine du projet)
#
# Cron (tous les jours à 2 h) :
#   0 2 * * * /chemin/vers/zabantu/scripts/backup_db.sh >> $HOME/backups/zabantu/backup.log 2>&1
#
# Restauration (à faire sur une base vide, après avoir arrêté l'application) :
#   pg_restore --no-owner -U <utilisateur> -h <hôte> -d <nom_base> zabantu_db_AAAA-MM-JJ_HHMM.dump
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib_backup.sh"

command -v pg_dump >/dev/null || fail "pg_dump introuvable (client PostgreSQL non installé ou hors du PATH)"

DB_NAME=$(env_get DB_NAME); DB_USER=$(env_get DB_USER); DB_PASSWORD=$(env_get DB_PASSWORD)
DB_HOST=$(env_get DB_HOST); DB_PORT=$(env_get DB_PORT)
[ -n "$DB_NAME" ] && [ -n "$DB_USER" ] || fail "DB_NAME ou DB_USER manquant dans $ENV_FILE"

mkdir -p "$BACKUP_DIR"
target="$BACKUP_DIR/zabantu_db_$(date +%F_%H%M).dump"
partial="$target.partial"
trap 'rm -f "$partial"' EXIT

log "sauvegarde de la base « $DB_NAME » vers $target"
# Le mot de passe passe par l'environnement du seul processus pg_dump, jamais par la ligne de commande.
PGPASSWORD="$DB_PASSWORD" pg_dump -Fc --no-owner -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "$DB_USER" -f "$partial" "$DB_NAME"

# Contrôle : fichier non vide et lisible par pg_restore, sinon la sauvegarde est refusée.
[ -s "$partial" ] || fail "la sauvegarde est vide"
if command -v pg_restore >/dev/null; then
  pg_restore --list "$partial" >/dev/null || fail "la sauvegarde est illisible par pg_restore"
fi
mv "$partial" "$target"
log "terminé : $(du -h "$target" | cut -f1)"

prune 'zabantu_db_*.dump'
