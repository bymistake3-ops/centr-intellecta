# Центр Интеллекта «Синергия» — бот мастер-класса «5 навыков мозга»

Telegram-бот `@intellectcentr_masterclass_bot` для мастер-класса
«5 навыков мозга, которые определяют всё» (Ольга Зеброва, ЦИ «Синергия»).

Автовебинар идёт ежедневно в **19:00 МСК**. Для каждого пользователя дата
эфира = следующий календарный день после регистрации.

## CRM-цепочка (Telegram-бот)

| Touch | Когда | Что |
|---|---|---|
| TG1 | мгновенно на `/start` | приветствие + дата эфира |
| TG1a | мгновенно следом | PDF «Карта из 5 шагов» |
| TG2 | день эфира, 10:00 МСК | утреннее напоминание |
| TG3 | за 30 мин до эфира | «открывайте» + inline-кнопка эфира |
| TG4 | за 5 мин | «начинаем» + inline-кнопка эфира |
| TG5 | +90 мин после старта (~20:30) | анонс бонусов + кодовое слово ПРОКАЧКА |
| TG6 | триггер: слово ПРОКАЧКА | ссылка на курс + PDF-чеклист «30 дней» |

Email-часть цепочки (E1–E4) и первичный захват контакта лендингом — **вне
скоупа этого репо**.

## Что редактирует владелец без кода

- **Тексты сообщений:** `content/messages.yaml` — см. [`docs/EDITING.md`](docs/EDITING.md)
- **PDF-бонусы:** `content/bonus.pdf` и `content/checklist.pdf` — через GitHub Web UI
- **Ссылки (эфир, курс):** Amvera → ENV → Restart
- **Кодовое слово:** Amvera → ENV `SECRET_WORD` → Restart

## Документация

- [`docs/DEPLOY.md`](docs/DEPLOY.md) — первый деплой на Amvera, пошагово
- [`docs/EDITING.md`](docs/EDITING.md) — как править тексты, PDF, ссылки
- [`docs/TESTING.md`](docs/TESTING.md) — smoke-тест всей цепочки за 4 минуты

## Структура

```
app/                 код бота (не редактировать без разработчика)
content/
  messages.yaml      все тексты и тайминги
  bonus.pdf          бонус за регистрацию (TG1a)
  bonus2.pdf         бонус после вебинара (TG6, по слову ПРОКАЧКА)
data/                persistent-диск рантайма: bot.db (в git не коммитится)
docs/                инструкции
.env.example         шаблон переменных окружения
requirements.txt     Python-зависимости
amvera.yml           конфиг деплоя
Dockerfile           фоллбек для переезда на VPS
```

## Стек

Python 3.11 · aiogram 3.13 · APScheduler 3.10 · SQLAlchemy 2 · SQLite

APScheduler хранит джобы в SQLite → напоминания переживают рестарт.

## Локальный запуск (для разработчика)

```bash
cp .env.example .env
# заполнить .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Безопасность

- Токен бота — только в Amvera ENV. В git не коммитится.
- `.env` и `*.db` — в `.gitignore`.
- Если токен утёк — `@BotFather` → `/revoke` → обнови `BOT_TOKEN` в Amvera.
