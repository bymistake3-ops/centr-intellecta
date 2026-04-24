# Centr Intellecta — Telegram-бот автовебинара

Telegram-бот для регистрации на автовебинар и отправки цепочки из 7 напоминаний:
мгновенный welcome+PDF → вечер дня регистрации → утро дня вебинара → за час →
за 5 мин → через 30 мин после старта → через сутки запись.

Автовебинар идёт ежедневно в **19:00 МСК**. Для каждого пользователя дата вебинара =
следующий календарный день после регистрации.

## Что уметь делать владельцу

- **Править тексты сообщений:** `content/messages.yaml` — см. `docs/EDITING.md`
- **Менять ссылки (эфир, запись, курс):** в переменных окружения Amvera
- **Проверить бота:** `SMOKE_TEST=true` — см. `docs/TESTING.md`

## Документация

- [`docs/DEPLOY.md`](docs/DEPLOY.md) — первый деплой на Amvera, пошагово
- [`docs/EDITING.md`](docs/EDITING.md) — как править тексты и ссылки без кода
- [`docs/TESTING.md`](docs/TESTING.md) — как прогнать всю цепочку за 6 минут

## Структура

```
app/                код бота (не редактировать без разработчика)
content/            редактируемый контент: messages.yaml, bonus.pdf
data/               persistent-диск рантайма: bot.db (в git не коммитится)
docs/               инструкции
.env.example        шаблон переменных окружения
requirements.txt    Python-зависимости
amvera.yml          конфиг деплоя
Dockerfile          если решишь переехать на VPS
```

## Стек

Python 3.11 · aiogram 3.13 · APScheduler 3.10 · SQLAlchemy 2 · SQLite

## Локальный запуск (для разработчика)

```bash
cp .env.example .env
# заполнить .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```
