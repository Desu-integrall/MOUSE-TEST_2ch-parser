# 🐁MOUSE-TEST_2ch-parser

![Лого](https://github.com/Desu-integrall/MOUSE-TEST_2ch-parser/blob/2ch-parser-updated/2ch-parser%20logo.png)

### Описание

Универсальный Python-скрипт для парсинга тредов с форума 2ch.hk с целью создания датасета для обучения чат-ботов.

Поддерживает как парсинг конкретных тредов, так и всей доски, с фильтрацией спама, коротких сообщений, цитат и мусора.

### Установка через консоль
```bash
git clone https://github.com/Desu-integrall/MOUSE-TEST_2ch-parser.git
```

```bash
cd MOUSE-TEST_2ch-parser && virtualenv venv && source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### Запуск

Парсинг досок:
```bash
python 2ch-parser.py -b b a po --limit 10
```

• -b — список досок.

• --limit — кол-во тредов с доски (default: 20).

Парсинг конкретных тредов:
```bash
python 2ch-parser.py -b b -t 319248888 319249111
```

• -t — список номеров тредов.

### Управление повторами

Скрипт не скачивает уже обработанные треды. Список хранится в processed_threads.json.

### Результат

Формат выходного JSON:
```bash
[
  {"role": "user", "content": "Анон, ты лох"},
  {"role": "assistant", "content": "Да, и горжусь этим!"}
]
```
