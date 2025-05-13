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
cd MOUSE-TEST_2ch-parser
```

```bash
python -m venv venv
```

```bash
venv\Scripts\activate.bat
```

```bash
pip install -r requirements.txt
```

### Запуск

Парсинг досок:
```bash
python 2ch-parser.py --boards b,a,po --limit 10 --output .\datasets
```

• --boards — список досок.

• --limit — кол-во тредов с доски (по дефолту парситься вся доска).

• --output - директория установки датасетов.

Парсинг конкретных тредов:
```bash
python 2ch-parser.py --boards b --threads 319248888,319249111 --output .\datasets
```

• --threads — список номеров тредов.

### Управление повторами

Скрипт не скачивает уже обработанные треды повторно, если указать аргумент:

• --skip-existing

Список обработанных тредов хранится в processed_threads.json.

### Результат

Формат выходного JSON:
```bash
[
  {"role": "user", "content": "Анон, ты лох"},
  {"role": "assistant", "content": "Да, и горжусь этим!"}
]
```
