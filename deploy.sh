#!/usr/bin/env bash
# Mise à jour de la production : sauvegardes, code de GitHub, dépendances, migrations, statiques, miniatures, contrôles.
# Détail et vérifications : docs/DEPLOIEMENT_PROD.md
#
# Usage sur le serveur (virtualenv cPanel) :
#   PYTHON=/home/cp2594820p30/virtualenv/repositories/zabantu/3.13/bin/python ./deploy.sh [username ...]
#   (les usernames reçoivent l'accès au backoffice)
# Réglages optionnels :
#   PYTHON=...       interpréteur du virtualenv (défaut : python)
#   BRANCH=main      branche à déployer
#   SKIP_BACKUP=1    ne pas sauvegarder avant (déconseillé)
#
# ATTENTION : « git reset --hard » aligne le code sur GitHub et ÉCRASE toute modification faite à la main sur les fichiers
# suivis par git. Le .env, media/ et les logs ne sont pas touchés. Ne jamais modifier le code directement sur le serveur.
set -euo pipefail

# Tout le script est lu avant d'être exécuté : « git reset » peut remplacer deploy.sh sans perturber l'exécution en cours.
main() {
  cd "$(dirname "$0")"
  PYTHON="${PYTHON:-python}"
  BRANCH="${BRANCH:-main}"

  if [ -z "${SKIP_BACKUP:-}" ]; then
    echo "==> sauvegarde de la base et des médias"
    bash scripts/backup_db.sh
    bash scripts/backup_media.sh
  fi

  echo "==> code : git fetch origin $BRANCH, puis alignement sur origin/$BRANCH"
  local modified
  modified=$(git status --porcelain --untracked-files=no)
  [ -z "$modified" ] || { echo "Modifications locales écrasées :"; echo "$modified"; }
  git fetch origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
  echo "Version déployée : $(git log --oneline -1)"

  echo "==> dépendances"
  $PYTHON -m pip install -r requirements.txt

  echo "==> migrations (plan, puis application)"
  $PYTHON manage.py migrate --plan
  $PYTHON manage.py migrate

  echo "==> collectstatic"
  $PYTHON manage.py collectstatic --noinput

  echo "==> generate_thumbnails"
  $PYTHON manage.py generate_thumbnails

  echo "==> check --deploy"
  $PYTHON manage.py check --deploy

  if [ "$#" -gt 0 ]; then
    echo "==> grant_backoffice_access $*"
    $PYTHON manage.py grant_backoffice_access "$@"
  fi

  echo "Terminé. Redémarrez l'application (cPanel > Setup Python App > Restart), puis suivez les vérifications de docs/DEPLOIEMENT_PROD.md (section 5)."
}

main "$@"
exit
