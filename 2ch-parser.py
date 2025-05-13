import requests
import json
import time
import re
import os
import argparse
from bs4 import BeautifulSoup
from typing import List, Dict, Set

# Базовый URL 2ch.hk
BASE_URL = "https://2ch.hk"

# Заголовки запроса, чтобы сервер думал, что это обычный браузер
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
}

# Имя файла, где будут сохраняться уже обработанные треды
PROCESSED_THREADS_FILE = "processed_threads.json"

# Загружаем обработанные треды из файла, чтобы не скачивать повторно
def load_processed_threads() -> Set[int]:
    if os.path.exists(PROCESSED_THREADS_FILE):
        with open(PROCESSED_THREADS_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

# Сохраняем ID обработанных тредов в файл
def save_processed_threads(processed: Set[int]):
    with open(PROCESSED_THREADS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(processed), f, ensure_ascii=False, indent=2)

# Получаем список тредов с доски (каталог JSON)
def fetch_threads(board: str) -> List[Dict]:
    url = f"{BASE_URL}/{board}/catalog.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    catalog = response.json()
    return catalog['threads']

# Загружаем содержимое конкретного треда и формируем пары user-assistant
def fetch_thread(board: str, thread_num: int) -> List[Dict]:
    url = f"{BASE_URL}/{board}/res/{thread_num}.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    posts = data['threads'][0]['posts']

    post_map = {}
    referenced_by = {}
    dialog_pairs = []

    # Собираем все сообщения и связи между ними по ссылкам >>
    for post in posts:
        if 'comment' in post and 'num' in post:
            cleaned = clean_html(post['comment'])
            if is_clean(cleaned):
                post_id = post['num']
                post_map[post_id] = cleaned
                refs = re.findall(r'>>([0-9]{5,10})', post['comment'])
                for ref in refs:
                    ref_num = int(ref)
                    if ref_num not in referenced_by:
                        referenced_by[ref_num] = []
                    referenced_by[ref_num].append(post_id)

    # Формируем пары (user -> assistant) на основе ссылок
    for user_id, assistant_ids in referenced_by.items():
        if user_id in post_map:
            for assistant_id in assistant_ids:
                if assistant_id in post_map:
                    user_text = remove_op_references(post_map[user_id])
                    assistant_text = remove_op_references(remove_quotes(post_map[assistant_id]))
                    dialog_pairs.append({"role": "user", "content": user_text})
                    dialog_pairs.append({"role": "assistant", "content": assistant_text})

    return dialog_pairs

# Удаляем HTML и >>ссылки из текста
def clean_html(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, 'html.parser')
    text = soup.get_text()
    text = re.sub(r">>\d{5,10}", "", text)
    return text.strip()

# Удаляем метку (OP)
def remove_op_references(text: str) -> str:
    return re.sub(r"\(\s*OP\s*\)", "", text, flags=re.IGNORECASE).strip()

# Удаляем цитаты, начинающиеся с '>'
def remove_quotes(text: str) -> str:
    lines = text.splitlines()
    filtered = [line for line in lines if not line.strip().startswith(">")]
    return "\n".join(filtered).strip()

# Фильтруем нежелательные сообщения по длине, ссылкам, символам, ключевым словам
def is_clean(text: str) -> bool:
    if len(text) < 10:
        return False
    if len(text.split()) < 2:
        return False
    if re.search(r'http[s]?://', text):
        return False
    if re.search(r'[<>\\/_]', text):
        return False
    if re.search(r'\b(?:sage|bump|муд|тред)\b', text, re.IGNORECASE):
        return False
    return True

# Сбор данных с доски или конкретных тредов
def collect_dataset(board: str, limit: int = None, thread_ids: List[int] = None, skip_existing=True) -> List[Dict]:
    if thread_ids:
        threads = [{'num': tid} for tid in thread_ids]
    else:
        threads = fetch_threads(board)
        if limit:
            threads = threads[:limit]

    dataset = []
    processed_threads = load_processed_threads()

    for thread in threads:
        thread_num = thread['num']
        if skip_existing and thread_num in processed_threads:
            continue
        try:
            dialog_pairs = fetch_thread(board, thread_num)
            dataset.extend(dialog_pairs)
            processed_threads.add(thread_num)
        except Exception as e:
            print(f"Error fetching thread {thread_num} on /{board}/: {e}")
        time.sleep(1)

    save_processed_threads(processed_threads)
    return dataset

# Сохраняем готовый датасет в файл
def save_dataset(dataset: List[Dict], filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

# Точка входа: разбираем аргументы командной строки и запускаем парсинг
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2ch.hk dataset parser")
    parser.add_argument("--boards", type=str, required=True, help="Список досок через запятую, например: b,po,news")
    parser.add_argument("--limit", type=int, default=None, help="Сколько тредов скачивать с каждой доски")
    parser.add_argument("--threads", type=str, default=None, help="Номера тредов через запятую (вместо limit)")
    parser.add_argument("--output", type=str, default=".", help="Папка для сохранения JSON-файлов")
    parser.add_argument("--skip-existing", action="store_true", help="Пропускать уже обработанные треды")

    args = parser.parse_args()

    boards = args.boards.split(',')
    thread_ids = [int(t) for t in args.threads.split(',')] if args.threads else None
    os.makedirs(args.output, exist_ok=True)

    for board in boards:
        print(f"\n=== Обработка доски /{board}/ ===")
        dataset = collect_dataset(board, limit=args.limit, thread_ids=thread_ids, skip_existing=args.skip_existing)
        output_path = os.path.join(args.output, f"2ch_{board}_dialog_dataset.json")
        save_dataset(dataset, output_path)
        print(f"Сохранено {len(dataset)} пар из /{board}/ в {output_path}")

