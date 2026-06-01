#!/usr/bin/env bash
# ============================================================
#  Фича Инструменты — установка
#  Запуск:  ./install.sh
# ============================================================
set -u  # ругаться на необъявленные переменные

# Папка, где лежит этот скрипт (чтобы запускать из любого места)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'; BOLD='\033[1m'; RESET='\033[0m'
say()  { echo -e "${GREEN}✓${RESET} $1"; }
warn() { echo -e "${YELLOW}!${RESET} $1"; }
err()  { echo -e "${RED}✗${RESET} $1"; }
head() { echo -e "\n${BOLD}$1${RESET}"; }

head "Фича Инструменты — установка"

# --- 1. Проверяем Python 3.11+ --------------------------------------------
PYTHON=""
for cand in python3.12 python3.11 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    VER="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
    MAJOR="${VER%%.*}"; MINOR="${VER##*.}"
    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
      PYTHON="$cand"; break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  err "Не найден Python 3.11 или новее."
  echo "  Установите его через Homebrew:  brew install python@3.12"
  echo "  Если нет Homebrew — поставьте его: https://brew.sh"
  exit 1
fi
say "Python найден: $($PYTHON --version)"

# --- 2. Виртуальное окружение ---------------------------------------------
if [ ! -d ".venv" ]; then
  head "Создаю виртуальное окружение (.venv)…"
  "$PYTHON" -m venv .venv || { err "Не удалось создать окружение."; exit 1; }
fi
# shellcheck disable=SC1091
source .venv/bin/activate
say "Окружение активировано."

# --- 3. Зависимости --------------------------------------------------------
head "Устанавливаю зависимости (это может занять пару минут)…"
python -m pip install --upgrade pip >/dev/null
if python -m pip install -r requirements.txt; then
  say "Зависимости установлены."
else
  err "Не удалось установить зависимости. Прокрутите вверх и прочитайте ошибку."
  exit 1
fi

# --- 4. Проверяем ffmpeg ---------------------------------------------------
head "Проверяю ffmpeg…"
if command -v ffmpeg >/dev/null 2>&1; then
  say "ffmpeg найден."
else
  warn "ffmpeg не найден."
  echo "  Он нужен для надёжной обработки аудио. Установите так:"
  echo "      brew install ffmpeg"
  echo "  (Если Homebrew не установлен — поставьте его с https://brew.sh)"
  echo "  Базовое распознавание может работать и без него, но лучше установить."
fi

# --- 5. Проверяем Ollama (необязательно) -----------------------------------
head "Проверяю Ollama (улучшение текста нейросетью)…"
if command -v ollama >/dev/null 2>&1; then
  say "Ollama установлена."
  echo "  Чтобы скачать модель улучшения текста, выполните:"
  echo "      ollama pull qwen2.5:7b"
else
  warn "Ollama не установлена — это НЕ ошибка."
  echo "  Без неё текст будет приводиться в порядок простой встроенной очисткой."
  echo "  Если захотите умное улучшение — установите Ollama с https://ollama.com"
  echo "  и выполните:  ollama pull qwen2.5:7b"
fi

head "Готово!"
echo -e "Теперь запустите сервис командой:  ${BOLD}./run.sh${RESET}"
echo -e "Или проверьте улучшатель без микрофона:  ${BOLD}./run.sh --test-text${RESET}"
