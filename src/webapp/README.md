# WebApp

Telegram Web App на React + Vite.

## Стек

- **React 18** — UI фреймворк
- **Vite** — сборщик
- **@twa-dev/twa-sdk** — Telegram SDK

## Структура

```
webapp/
├── src/
│   ├── components/  # Компоненты
│   ├── pages/        # Страницы
│   ├── hooks/        # React hooks
│   └── services/    # API сервисы
├── public/           # Статика
└── package.json
```

## Запуск

```bash
cd src/webapp
npm install
npm run dev
```

## Сборка

```bash
npm run build
```

## Telegram Web App

Telegram Web App запускается через кнопку `web_app` в боте:

```python
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

button = KeyboardButton(text="Открыть", web_app=WebAppInfo(url="https://..."))
keyboard = ReplyKeyboardMarkup(keyboard=[[button]])
```

## Использование Telegram SDK

```typescript
import WebApp from '@twa-dev/twa-sdk';

WebApp.ready();
WebApp.expand();
WebApp.close();
```