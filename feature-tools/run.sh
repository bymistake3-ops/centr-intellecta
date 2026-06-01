#!/usr/bin/env bash
# ============================================================
#  Фича Инструменты — запуск
#  Обычный запуск:        ./run.sh
#  Тест текста:           ./run.sh --test-text
#  Разовая запись:        ./run.sh --record-once
#  Список устройств:      ./run.sh --list-devices
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

RED='\033[31m'; BOLD='\033[1m'; RESET='\033[0m'

if [ ! -d ".venv" ]; then
  echo -e "${RED}✗${RESET} Окружение не найдено. Сначала выполните: ${BOLD}./install.sh${RESET}"
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# Передаём все аргументы дальше (например, --test-text)
exec python -m app.main "$@"
