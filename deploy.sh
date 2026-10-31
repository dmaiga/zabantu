#!/usr/bin/env bash
# Déploiement : migrate, statiques, miniatures, accès au backoffice.
# Usage : ./deploy.sh [username ...]   (les usernames reçoivent l'accès au backoffice)
# Prérequis : sauvegarde de la base faite (docs/DEPLOIEMENT_PROD.md, section 2).
set -euo pipefail

cd "$(dirname "$0")"
PYTHON="${PYTHON:-python}"

echo "==> migrate"
$PYTHON manage.py migrate

echo "==> collectstatic"
$PYTHON manage.py collectstatic --noinput

echo "==> generate_thumbnails"
$PYTHON manage.py generate_thumbnails

if [ "$#" -gt 0 ]; then
  echo "==> grant_backoffice_access $*"
  $PYTHON manage.py grant_backoffice_access "$@"
fi

echo "Terminé. Pensez à redémarrer l'application (gunicorn, Passenger…)."
