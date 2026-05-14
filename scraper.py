import os
import requests
from bs4 import BeautifulSoup
import re

# Создаем папку для файлов, если её нет
if not os.path.exists('raw_data'):
    os.makedirs('raw_data')

# Ссылка на раздел цен СЗПТ
url = "https://stat.gov.kz/ru/industries/economy/prices/spreadsheets/?year=&name=19060&period=&type=spreadsheets"

def download_files():
    print("Начинаю сбор ссылок...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Ошибка при доступе к сайту: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Регулярное выражение для поиска ссылок на файлы
    links = soup.find_all('a', href=re.compile(r'/api/iblock/element/\d+/file/ru/'))
    
    print(f"Найдено потенциальных ссылок: {len(links)}")
    
    for link in links:
        try:
            file_url = "https://stat.gov.kz" + link['href']
            file_id = link['href'].split('/')[-4]
            
            # Ищем дату в тексте родительского контейнера (строки таблицы)
            parent_row = link.find_parent('div', class_='table-row') or link.find_parent()
            parent_text = parent_row.get_text()
            
            date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', parent_text)
            
            if date_match:
                date_str = date_match.group(0)
                # Форматируем дату для имени файла (ДД.ММ.ГГГГ -> ГГГГ-ММ-ДД)
                clean_date = "-".join(date_str.split('.')[::-1])
            else:
                clean_date = f"unknown_{file_id}"
            
            # ИСПРАВЛЕНО: Меняем .xlsx на .xls
            file_path = f'raw_data/{clean_date}.xls'
            
            # Проверка, чтобы не скачивать повторно уже существующие файлы
            if os.path.exists(file_path):
                print(f"Пропуск: {clean_date} уже существует.")
                continue

            print(f"Скачиваю: {clean_date} (ID: {file_id})...")
            r = requests.get(file_url, stream=True)
            if r.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
        except Exception as e:
            print(f"Ошибка при обработке файла {file_id}: {e}")

    print("-" * 30)
    print(f"Готово! Проверьте папку 'raw_data'. Теперь файлы сохранены в .xls")

if __name__ == "__main__":
    download_files()