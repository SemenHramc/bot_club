# Техническая спецификация

## 1. Архитектура

Компоненты системы:

- Telegram Bot
- Backend (API сервер)
- База данных
- Интеграция с Т-Банком
- Планировщик задач

---

## 2. Стек (рекомендуемый)

- Backend: Python (FastAPI) / Node.js
- Telegram: Bot API
- БД: PostgreSQL
- Планировщик: cron / Celery / APScheduler

---

## 3. Интеграция с Т-Банком

### 3.1 Требуемые данные

- TerminalKey
- Secret (Password)
- webhook URL

---

### 3.2 Поток оплаты

1. Backend создаёт платёж
2. Получает ссылку
3. Передаёт пользователю
4. Получает webhook
5. Обрабатывает статус

---

## 4. База данных

### Таблица users

- id
- telegram_id
- fio
- phone
- email
- created_at

---

### Таблица subscriptions

- id
- user_id
- start_date
- end_date
- status

---

### Таблица payments

- id
- user_id
- amount
- promo_code
- status
- created_at

---

### Таблица promo_codes

- id
- code
- value
- owner
- active
- usage_count

---

## 5. API (внутренние)

### Создание платежа

POST /create-payment

---

### Проверка оплаты

POST /webhook

---

### Получение ссылки доступа

POST /get-invite

---

## 6. Telegram API

Используется:

- createChatInviteLink
- banChatMember
- unbanChatMember

---

## 7. Планировщик

Ежедневные задачи:

- проверка окончания подписок
- отправка напоминаний
- удаление пользователей

---

## 8. Логирование

Обязательно логировать:

- платежи
- ошибки webhook
- выдачу доступа
- удаление пользователей

---

## 9. Безопасность

- хранение секретов в env
- проверка подписи webhook
- защита API

---

## 10. Масштабируемость

- возможность увеличения нагрузки
- добавление новых ботов
- расширение логики подписок
