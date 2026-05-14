import pandas as pd
import os
import glob
import re

def process_data():
    all_data = []
    # Путь к папке с файлами
    file_list = glob.glob("raw_data/*.xls")
    
    
    # Словарь для нормализации названий товаров
        product_mapping = {
        'Яйца, 1 категории, десяток': 'Яйца, 1 категории',
        'Кефир 2,5%, литр': 'Кефир 2-3% жирности',
        'Кефир 2-3% жирности, литр': 'Кефир 2-3% жирности',
        'Кефир 2,5%': 'Кефир 2-3% жирности',
        'Масло подсолнечное, литр': 'Масло подсолнечное',
        'Масло сливочное несоленое': 'Масло сливочное',
        'Молоко пастеризованное 2,5%, литр': 'Молоко (пастеризованное, ультрапастеризованное, стерилизованное от 2,2% до 6% жирности)',
        'Молоко (пастеризованное, ультрапастеризованное, стерилизованное от 2,2% до 6% жирности), литр': 'Молоко (пастеризованное, ультрапастеризованное, стерилизованное от 2,2% до 6% жирности)',
        'Крупа гречневая (весовая)': 'Крупа гречневая',
        'Говядина лопаточно-грудная часть': 'Говядина',
        'Говядина с костями': 'Говядина',
        'Говядина бескостная': 'Говядина',
        'Баранина, включая бескостную': 'Баранина',
        'Мясо кур (бедренная и берцовая кость с прилегающей к ней мякотью)': 'Мясо кур',
        'Мясо кур (бедро, голень, окорочка куриные)': 'Мясо кур',
        'Куры': 'Мясо кур',
        'Рожки (весовые)': 'Рожки',
        'Соль, кроме экстра': 'Соль',
        'Творог 5-9% жирности': 'Творог',
        'Рис шлифованный, полированный (весовой)': 'Рис',
        'Рис шлифованный': 'Рис'
    }

    for file_path in file_list:
        try:
            report_date = os.path.basename(file_path).replace(".xls", "")
            
            # 1. Открываем файл и выбираем нужный лист
            xls = pd.ExcelFile(file_path, engine='xlrd')
            sheet_names = xls.sheet_names
            
            # Если есть лист с именем "5" — берем его, иначе берем самый последний
            if "5" in sheet_names:
                target_sheet = "5"
            else:
                target_sheet = sheet_names[-1]
            
            # 2. Ищем строку-заголовок (где города)
            df_raw = pd.read_excel(xls, sheet_name=target_sheet, header=None)
            header_idx = 0
            for i in range(min(15, len(df_raw))):
                row_vals = [str(val) for val in df_raw.iloc[i].values]
                if any("Астана" in v for v in row_vals):
                    header_idx = i
                    break
            
            # 3. Читаем данные с найденного заголовка
            df = pd.read_excel(xls, sheet_name=target_sheet, skiprows=header_idx)
            
            # 4. Базовая очистка структуры
            df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
            df.rename(columns={df.columns[0]: 'Product'}, inplace=True)
            
            # Оставляем только Product и города (убираем "Unnamed", "период", "процент")
            cols_to_keep = [c for c in df.columns if "Product" in str(c) or 
                            (not "Unnamed" in str(c) and "период" not in str(c).lower() and "процент" not in str(c).lower())]
            df = df[cols_to_keep]
            df = df[df['Product'].notna()]
            
            # 5. Трансформация в длинный формат (Melt)
            df_long = df.melt(id_vars=['Product'], var_name='City', value_name='Price')
            
            # 6. ОЧИСТКА ГОРОДОВ
            # Убираем технический мусор из City
            trash_words = ['период', 'начало', 'справочно', 'январь', 'февраль', 'март', 'апрель']
            for word in trash_words:
                df_long = df_long[~df_long['City'].astype(str).str.contains(word, case=False)]

            # Удаляем строки с общими агрегатами вместо конкретных городов
            df_long = df_long[~df_long['City'].str.contains('По обследованным городам|средние цены', case=False, na=False)]
            
            # Удаляем сноски типа " 1)" или "2)" из городов
            df_long['City'] = df_long['City'].astype(str).str.replace(r'\d+\)', '', regex=True)
            df_long['City'] = df_long['City'].str.replace(r'\d+', '', regex=True).str.strip()

            # 7. ОЧИСТКА ТОВАРОВ (PRODUCT)
            df_long['Product'] = df_long['Product'].astype(str).str.strip()
            
            # Удаляем сноски типа " 1)" из товаров
            df_long['Product'] = df_long['Product'].str.replace(r'\s*\d+\)', '', regex=True)
            
            # Применяем маппинг (нормализация названий)
            df_long['Product'] = df_long['Product'].replace(product_mapping)
            
            # Убираем лишние пробелы (двойные в один)
            df_long['Product'] = df_long['Product'].str.replace(r'\s+', ' ', regex=True).str.strip()
            
            # 8. Финализация данных файла
            df_long['Date'] = report_date
            all_data.append(df_long)
            
        except Exception as e:
            print(f"Ошибка в файле {file_path}: {e}")

    # 9. ОБЪЕДИНЕНИЕ И СОХРАНЕНИЕ
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Преобразование цен в числа
        final_df['Price'] = pd.to_numeric(final_df['Price'], errors='coerce')
        final_df = final_df.dropna(subset=['Price'])
        
        # Сохранение в CSV
        output_file = "kazakhstan_inflation_final_v2.csv"
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print("-" * 30)
        print(f"Успешно обработано файлов: {len(all_data)}")
        print(f"Итого строк в датасете: {len(final_df)}")
        print(f"Файл сохранен как: {output_file}")
    else:
        print("Данные не были собраны.")

if __name__ == "__main__":
    process_data()
