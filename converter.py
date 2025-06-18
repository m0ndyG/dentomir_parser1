import json
import pandas as pd
import os

def convert_json_to_xlsx(json_path='products.json', xlsx_path='products.xlsx'):
    if not os.path.exists(json_path):
        print(f"Ошибка: Исходный файл не найден по пути '{json_path}'")
        print("Сначала запустите паука командой: scrapy crawl dentomir -o products.json")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Ошибка: Файл '{json_path}' пуст или имеет неверный формат.")
            return

    if not data:
        print("JSON-файл пуст. Нет данных для конвертации.")
        return
    df = pd.DataFrame(data)

    if 'image_urls' in df.columns:
        df['image_urls'] = df['image_urls'].apply(
            lambda urls: '\n'.join(urls) if isinstance(urls, list) else ''
        )
    columns_order = [
        'name',
        'sku',
        'price_regular',
        'availability',
        'category',
        'brand',
        'rating',
        'review_count',
        'description',
        'url',
        'image_urls'
    ]
    final_columns = [col for col in columns_order if col in df.columns]
    df = df[final_columns]

    try:
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        print(f"✅ Конвертация успешно завершена. Данные сохранены в '{xlsx_path}'")
    except Exception as e:
        print(f"❌ Произошла ошибка при сохранении в Excel: {e}")


if __name__ == '__main__':
    convert_json_to_xlsx()