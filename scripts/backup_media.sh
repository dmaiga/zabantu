#!/usr/bin/env bash
# Sauvegarde du dossier media (images et PDF téléversés) de Zabantu, en archive compressée.
# Les miniatures (cache/thumbs) sont exclues : elles se régénèrent avec « manage.py generate_thumbnails ».
#
# Usage :   ./scripts/backup_media.sh
# Réglages optionnels (variables d'environnement) :
#   MEDIA_ROOT  dossier à sauvegarder        (défaut : MEDIA_ROOT du .env, sinon ./media)
#   BACKUP_DIR  dossier des sauvegardes      (défaut : ~/backups/zabantu, hors de public_html)
#   KEEP_DAYS   durée de conservation, jours  (défaut : 14)
#   ENV_FILE    fichier .env à lire           (défaut : .env à la racine du projet)
#
# Cron (tous les jours à 2 h 30) :
#   30 2 * * * /chemin/vers/zabantu/scripts/backup_media.sh >> $HOME/backups/zabantu/backup.log 2>&1
#
# Restauration : tar -xzf zabantu_media_AAAA-MM-JJ_HHMM.tar.gz -C <dossier parent de media>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib_backup.sh"

MEDIA_ROOT="${MEDIA_ROOT:-$(env_get MEDIA_ROOT)}"
MEDIA_ROOT="${MEDIA_ROOT:-$ROOT_DIR/media}"
MEDIA_ROOT="${MEDIA_ROOT%/}"
[ -d "$MEDIA_ROOT" ] || fail "dossier media introuvable : $MEDIA_ROOT"

mkdir -p "$BACKUP_DIR"
target="$BACKUP_DIR/zabantu_media_$(date +%F_%H%M).tar.gz"
partial="$target.partial"
trap 'rm -f "$partial"' EXIT

log "sauvegarde de $MEDIA_ROOT vers $target"
folder="$(basename "$MEDIA_ROOT")"
tar -czf "$partial" --exclude="$folder/cache/thumbs" -C "$(dirname "$MEDIA_ROOT")" "$folder"

# Contrôle : l'archive doit être lisible de bout en bout.
tar -tzf "$partial" >/dev/null || fail "l'archive est illisible"
mv "$partial" "$target"
log "terminé : $(du -h "$target" | cut -f1)"

prune 'zabantu_media_*.tar.gz'
