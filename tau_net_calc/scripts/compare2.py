import pandas as pd

def merge_csv_by_destination(file1, file2, output_file):
    # Загрузка данных из файлов
    df1 = pd.read_csv(file1, usecols=["Destination_ID", "Duration"], dtype={"Destination_ID": str})
    df2 = pd.read_csv(file2, usecols=["Destination_ID", "Duration"], dtype={"Destination_ID": str})
    
    # Переименование столбцов для различия
    df1.rename(columns={"Duration": "schedule"}, inplace=True)
    df2.rename(columns={"Duration": "fix"}, inplace=True)
    
    # Объединение данных по destination_id
    merged_df = pd.merge(df1, df2, on="Destination_ID", how="inner")

    # Подсчет случаев, когда duration2 > duration1
    count_greater = (merged_df["fix"] >= merged_df["schedule"]).sum()
    percent_greater = (count_greater / len(merged_df)) * 100 if len(merged_df) > 0 else 0
    
    # Сохранение результата в CSV
    merged_df.to_csv(output_file, index=False)
    
    print(f"duration2 > duration1: {count_greater}")
    print(f"%: {percent_greater:.2f}%")
    print(f"ok")


file1 = r"c:\temp\1\compare\250310_091700_PFSA.csv"
file2 = r"c:\temp\1\compare\250310_091511_PFXA.csv"
res = r"c:\temp\1\compare\compare.csv"
merge_csv_by_destination(file1, file2, res)
