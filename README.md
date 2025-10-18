# Biggle — MVP (Monorepo)

Монорепозиторий для MVP цифрового летающего ассистента **Biggle**.

## Структура
- `apps/mobile` — мобильное приложение (Flutter). На этапе MVP: экран приветствия + тест голосового ввода/вывода.
- `services/api` — FastAPI-сервис: аутентификация (стаб), базовый чат, заглушки для TTS/STT.
- `services/realtime` — WebSocket/RTC слой (позже).
- `packages/common` — общие модели/схемы (pydantic), константы, протоколы.
- `infra` — docker-compose, локальный запуск стека.
- `.github/workflows` — CI для backend.

## Быстрый старт (локально)
```bash
# 1) Клонируй репозиторий и перейди в services/api
cd services/api

# 2) Создай и активируй venv (Python 3.10+)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) Установи зависимости
pip install -r requirements.txt

# 4) Запусти API (http://127.0.0.1:8000)
./uvicorn_start.sh   # Windows: python -m uvicorn app.main:app --reload
```

## Быстрый старт через Docker
```bash
cd infra
docker compose up --build
```

## API (черновик)
- `GET /health` — проверка живости.
- `POST /auth/signup` — заглушка регистрации.
- `POST /auth/login` — заглушка логина, возвращает фейковый токен.
- `POST /chat/message` — принимает текст, отдаёт эхо-ответ (заглушка).

## Ветвление
- `main` — стабильная ветка.
- `dev` — активная разработка.
- PR из feature-веток -> `dev`, затем релиз в `main`.

## Лицензия
MIT — см. LICENSE.
