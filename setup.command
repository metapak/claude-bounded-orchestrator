#!/bin/sh
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
printf '%s\n' '+=================================================================='
printf '%s\n' '| Claude Bounded Orchestrator - guided installer                  |'
printf '%s\n' '| Native team: Anthropic Claude only                              |'
printf '%s\n' '+=================================================================='
if [ "$#" -gt 0 ]; then
  TARGET_INPUT=$1
else
  printf '\nDrag the target project folder here, then press Return.\n'
  printf 'Leave empty to use: %s\n> ' "$(pwd)"
  IFS= read -r TARGET_INPUT || TARGET_INPUT=''
fi
TARGET=${TARGET_INPUT:-"$(pwd)"}
TARGET=$(printf '%s' "$TARGET" | sed 's/[[:space:]]*$//;s/\\ / /g')
case "$TARGET" in
  \"*\") TARGET=$(printf '%s' "$TARGET" | sed 's/^"//;s/"$//') ;;
  \'*\') TARGET=$(printf '%s' "$TARGET" | sed "s/^'//;s/'$//") ;;
esac

printf '\nAction\n'
printf '%s\n' '  1. Safe install or update'
printf '%s\n' '  2. Dry-run preview (no files changed)'
printf '%s\n' '  3. Uninstall unchanged managed files'
printf 'Select [1]: '
IFS= read -r ACTION || ACTION=''
ACTION=${ACTION:-1}

set -- "$TARGET"
case "$ACTION" in
  1) set -- "$@" --interactive ;;
  2) set -- "$@" --interactive --dry-run ;;
  3) set -- "$@" --uninstall ;;
  *) printf '\nError: choose 1, 2, or 3.\n' >&2; STATUS=2; printf '\nPress Return to close.\n'; IFS= read -r _; exit "$STATUS" ;;
esac

python3 "$ROOT/scripts/install.py" "$@"
STATUS=$?
printf '\nInstaller exited with status %s.\n' "$STATUS"
printf 'Press Return to close this window.\n'
IFS= read -r _ || true
exit "$STATUS"
