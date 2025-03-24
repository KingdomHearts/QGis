import pandas as pd

def filter_and_extract(file1, file2, str1, str2):
    # Читаем первый файл
    df1 = pd.read_csv(file1)
    
    # Фильтруем по route_id
    filtered_df1 = df1[df1['route_id'] == str1]
    
    # Получаем список значений trip_id
    trip_ids = set(filtered_df1['trip_id'])
    
    # Читаем второй файл
    df2 = pd.read_csv(file2)
    
    # Оставляем только строки с найденными trip_id
    df2_filtered = df2[df2['trip_id'].isin(trip_ids)]
    
    # Фильтруем по stop_id
    df2_filtered = df2_filtered[df2_filtered['stop_id'] == str2]
    
    # Выводим значения arrival_time
    print(df2_filtered['arrival_time'].tolist())

# Использование
file1 = r"c:\doc\Игорь\GIS\PKL\PKL2025-2\GTFS\gtfs_09feb_08h42m16s\trips.txt"
file2 = r"c:\doc\Игорь\GIS\PKL\PKL2025-2\GTFS\gtfs_09feb_08h42m16s\stop_times.txt"
str1 = "26983_1"
str2 = "13471"
filter_and_extract(file1, file2, str1, str2)