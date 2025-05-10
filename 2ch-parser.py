import requests
import json
import re
import os
import argparse
from bs4 import BeautifulSoup
from typing import List, Dict, Set

# Базовый URL для 2ch
BASE_URL = "https://2ch.hk"

# Заголовки HTTP-запроса для имитации браузера
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
}

# Путь к файлу, в котором хранятся ID уже обработанных тредов
PROCESSED_THREADS_FILE = "processed_threads.json"
# Путь к общему файлу датасета
DATASET_FILE = "dialog_dataset.json"

# Загружает список уже обработанных тредов из файла
# Используется для избежания повторной обработки
def load_processed_threads() -> Set[int]:
    if os.path.exists(PROCESSED_THREADS_FILE):
        with open(PROCESSED_THREADS_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

# Сохраняет обновлённый список обработанных тредов в файл
def save_processed_threads(processed: Set[int]):
    with open(PROCESSED_THREADS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(processed), f, ensure_ascii=False, indent=2)

# Добавляет новые пары диалогов в общий JSON-файл
def append_to_dataset(pairs: List[Dict]):
    existing = []
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    existing.extend(pairs)
    with open(DATASET_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

# Очищает HTML-комментарий от тегов, ссылок на посты, маркеров (OP) и запрещённых символов
def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    text = re.sub(r">>\d{5,10}", "", text)
    text = re.sub(r"\(\s*OP\s*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[<>\\/_]", "", text)
    return text.strip()

# Удаляет строки-цитаты, начинающиеся с символа '>'
def remove_quotes(text: str) -> str:
    return "\n".join([line for line in text.splitlines() if not line.strip().startswith(">")]).strip()

# Проверяет, стоит ли включать текст в датасет
def is_clean(text: str) -> bool:
    if len(text) < 10 or len(text.split()) < 2:
        return False
    if re.search(r'http[s]?://', text):
        return False
    if re.search(r'[<>\\/_]', text):
        return False
    if re.search(r'\b(?:sage|bump|муд|тред)\b', text, re.IGNORECASE):
        return False
    return True

# Загружает и обрабатывает конкретный тред
# Возвращает пары user-assistant
def fetch_single_thread(board: str, thread_num: int) -> List[Dict]:
    url = f"{BASE_URL}/{board}/res/{thread_num}.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    posts = data['threads'][0]['posts']

    post_map = {}
    referenced_by = {}
    dialog_pairs = []

    for post in posts:
        if 'comment' in post and 'num' in post:
            cleaned = clean_text(post['comment'])
            if is_clean(cleaned):
                post_id = post['num']
                post_map[post_id] = cleaned
                refs = re.findall(r'>>([0-9]{5,10})', post['comment'])
                for ref in refs:
                    ref_num = int(ref)
                    if ref_num not in referenced_by:
                        referenced_by[ref_num] = []
                    referenced_by[ref_num].append(post_id)

    for user_id, assistant_ids in referenced_by.items():
        if user_id in post_map:
            for assistant_id in assistant_ids:
                if assistant_id in post_map:
                    assistant_text = remove_quotes(post_map[assistant_id])
                    dialog_pairs.append({"role": "user", "content": post_map[user_id]})
                    dialog_pairs.append({"role": "assistant", "content": assistant_text})

    return dialog_pairs

# Загружает список тредов с доски, ограничивая лимитом (по умолчанию 20)
# Возвращает список номеров тредов
def fetch_threads_from_board(board: str, limit: int = 20) -> List[int]:
    url = f"{BASE_URL}/{board}/catalog_num.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    thread_ids = []
    for thread in data['threads']:
        thread_ids.append(thread['num'])
        if limit and len(thread_ids) >= limit:
            break
    return thread_ids

# Главная точка входа, поддерживает запуск через параметры консоли
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Универсальный парсер 2ch.hk для сбора диалогов.")
    parser.add_argument("-b", "--boards", nargs='+', required=True, help="Список досок (например: b a po)")
    parser.add_argument("-t", "--threads", nargs='+', type=int, help="Конкретные треды по номерам")
    parser.add_argument("--limit", type=int, default=20, help="Ограничение на количество тредов при сборе с доски")

    args = parser.parse_args()
    boards = args.boards
    manual_threads = args.threads
    limit = args.limit

    processed = load_processed_threads()

    for board in boards:
        if manual_threads:
            thread_ids = manual_threads
        else:
            thread_ids = fetch_threads_from_board(board, limit)

        for thread_num in thread_ids:
            if thread_num in processed:
                print(f"Thread {thread_num} already processed, skipping.")
                continue

            try:
                dataset = fetch_single_thread(board, thread_num)
                append_to_dataset(dataset)
                print(f"Appended {len(dataset)} dialog entries from thread {thread_num} on /{board}/.")
                processed.add(thread_num)
            except Exception as e:
                print(f"Failed to process thread {thread_num} on /{board}/: {e}")

    save_processed_threads(processed)
