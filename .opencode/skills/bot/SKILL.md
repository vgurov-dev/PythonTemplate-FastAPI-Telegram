---
name: bot-handlers
description: Telegram bot inline keyboard handling patterns
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: telegram
---

# Bot Skill

## Inline Keyboard Handling

При работе с inline-keyboard кнопками всегда соблюдать:

1. **Удаление сообщения** — после нажатия кнопки удалять текущее сообщение с клавиатурой
2. **Создание нового ответа** — отправлять новое сообщение вместо старого
3. **Обязательный answer()** — завершать callback ответом, чтобы убрать "часики" с кнопки

## Пример

```python
@router.callback_query()
async def handle_button(callback: CallbackQuery):
    await callback.answer()  # 1. Убираем часики
    await callback.message.delete()  # 2. Удаляем сообщение с клавиатурой
    await callback.message.answer("Новое сообщение")  # 3. Создаём ответ
```

## Почему это важно

- Не плодить дублирующиеся сообщения в чате
- Пользователь видит актуальное состояние интерфейса
- Интерфейс остаётся чистым