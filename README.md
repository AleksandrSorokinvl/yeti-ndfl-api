# Автозаполнение справки КНД 1151158 — как это работает

Клиент → форма на сайте → Make.com → это API (заполняет PDF) → письмо на
`kometa.dreamski@gmail.com` и документ в Telegram-бота `@Yeti_form_bot`.

Всё уже написано и проверено локально (`fill_certificate.py` — точное
заполнение полей бланка, `api.py` — обёртка в виде веб-запроса). Осталось
выложить `api.py` в интернет (5 минут, бесплатно) и собрать сценарий в
Make.com (без кода, руками в конструкторе).

## 1. Деплой API на Render.com (бесплатно)

1. Создайте приватный репозиторий на GitHub и залейте туда папку `ndfl-tools/`
   (файлы `api.py`, `fill_certificate.py`, `template.pdf`, `requirements.txt`).
2. На [render.com](https://render.com) → **New → Web Service** → подключите
   этот репозиторий.
3. Настройки:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Environment variable:** `API_KEY` = придумайте длинный случайный пароль
     (например, сгенерируйте на [1password.com/password-generator](https://1password.com/password-generator) — 32+ символов). Этот
     ключ защищает эндпоинт от посторонних запросов.
4. После деплоя Render даст вам URL вида
   `https://yeti-ndfl.onrender.com`. Проверить: откройте
   `https://yeti-ndfl.onrender.com/health` — должно вернуть `{"status":"ok"}`.

**Перед этим шагом обязательно поправьте в `fill_certificate.py`:**
- `ORG_KPP` — сейчас пусто, нужен реальный КПП организации.
- `signer_name` — сейчас в примере заглушка «Директор Директорович
  Директоров»; в реальном сценарии это значение будет приходить из Make
  (шаг 3 ниже), но проверьте, что вы используете настоящее ФИО
  подписанта.

## 2. Подключение формы на сайте (уже сделано)

В `_preview-ndfl.html` форма при отправке шлёт `fetch()` с JSON прямо на
вебхук Make.com (см. константу `MAKE_WEBHOOK_URL` в конце файла — впишите
туда URL, который Make выдаст на шаге 3.1).

## 3. Сценарий в Make.com

Создайте новый сценарий, модули по порядку:

### 3.1 Webhooks → Custom webhook (триггер)
Создаст URL вида `https://hook.eu1.make.com/xxxxxxxx`. Вставьте его в
`MAKE_WEBHOOK_URL` в `_preview-ndfl.html`.

### 3.2 Tools → Set variable (данные сотрудника, вручную заполняемые по факту оплаты)
Здесь удобно остановить сценарий и **сначала уведомить вас**, а сумму и
номер справки проставить вручную позже — см. вариант Б ниже. Для быстрого
старта (вариант А) просто задайте:
- `cert_number` = `{{formatDate(now; "YYYYMMDDHHmmss")}}` (уникальный номер)
- `signer_name` = реальное ФИО директора/уполномоченного
- `sign_date` = `{{formatDate(now; "YYYY-MM-DD")}}`
- `amount_rub` = оставить пустым — впишете вручную в готовый PDF при
  необходимости (Sумма — единственное поле, которое небезопасно доверять
  автоматике, см. ниже «Важно про сумму»).

### 3.3 HTTP → Make a request
- **URL:** `https://yeti-ndfl.onrender.com/fill-certificate`
- **Method:** POST
- **Headers:** `Content-Type: application/json`, `X-Api-Key: <ваш API_KEY>`
- **Body type:** raw / JSON, тело — все поля из вебхука (шаг 3.1) плюс
  `cert_number`, `signer_name`, `sign_date`, `amount_rub` из шага 3.2.
- **Parse response:** выключено (нужен бинарный PDF, не JSON) — включите
  опцию "Return entire response" / сохраните как файл (в Make это делается
  через "Download file" в HTTP-модуле, либо сразу передайте бинарный вывод
  следующему модулю как attachment).

### 3.4 Email → Send an email (Gmail/Google Workspace модуль Make)
- To: `kometa.dreamski@gmail.com`
- Тема: `Новая заявка на справку КНД 1151158 — {{payer_name}} / {{student_name}}`
- Текст: коротко данные заявки для быстрой проверки.
- Attachment: файл из шага 3.3.

### 3.5 Telegram Bot → Send a Document
- Подключите `@Yeti_form_bot` в Make (Add connection → вставьте токен бота
  от @BotFather, если ещё не подключали).
- Chat: выберите чат/группу, куда слать (нужно один раз написать боту
  что-нибудь, чтобы он появился в списке чатов Make).
- Document: файл из шага 3.3.
- Caption: те же данные заявки, что и в письме.

Готово — после этого при каждой заявке с сайта вам на почту и в Telegram
будет прилетать заполненный PDF-черновик справки на проверку.

## Важно про сумму расходов

Скрипт **намеренно не берёт сумму оплаты у клиента** — клиент не должен
указывать её сам (может ошибиться или указать не то, что фактически
оплачено, а справка — официальный документ для налоговой). Два рабочих
варианта:

- **Вариант А (быстрее для клиента):** сумму оставляем пустой в
  автосгенерированном PDF, сотрудник дописывает её от руки/в Adobe Reader
  перед отправкой клиенту, сверившись с оплатами в 1С/CRM.
- **Вариант Б (надёжнее):** перед шагом 3.3 добавьте модуль, который ищет
  сумму оплат клиента за год в вашей учётной системе (если она даёт API —
  1С, YCLIENTS, Google Sheets с оплатами и т.п.), и подставляет её
  автоматически. Если оплаты ведутся в Google Таблице — это несложно
  добавить, скажите, и я соберу такой шаг.

## Локальный тест без деплоя

```bash
cd ndfl-tools
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
API_KEY=testkey uvicorn api:app --reload
# в другом терминале:
curl -s -X POST http://127.0.0.1:8000/fill-certificate \
  -H "Content-Type: application/json" -H "X-Api-Key: testkey" \
  -d @sample_data.json -o test.pdf
```
