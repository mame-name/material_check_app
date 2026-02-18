import pandas as pd
import numpy as np

def process_files_and_create_sim(df_req, df_inv):
    # 1. 前処理
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    
    # 2. 現在の在庫合計を算出 (品番ごと)
    # 【工程順計】を除外して、合計在庫数を集計
    df_inv_clean = df_inv[~df_inv['製造実績番号'].astype(str).contains('計')]
    current_stock = df_inv_clean.groupby('品番')['合計在庫数'].sum().to_dict()
    
    # 3. 所要量のピボット作成 (品番×要求日)
    pivot_req = df_req.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum'
    ).fillna(0)
    
    # 4. シミュレーション計算
    rows = []
    dates = pivot_req.columns
    
    for (code, name), req_row in pivot_req.iterrows():
        # 初期在庫を取得
        initial_stock = current_stock.get(code, 0)
        
        # 1行目: 使用量行
        usage_row = {'品番': code, '品名': name, '区分': '使用量', '現在庫': initial_stock}
        # 2行目: 在庫残行
        stock_row = {'品番': code, '品名': name, '区分': '在庫残', '現在庫': '-'}
        
        temp_stock = initial_stock
        for date in dates:
            usage = req_row[date]
            temp_stock -= usage  # 前日の在庫 - 当日の使用量
            
            usage_row[date] = usage if usage != 0 else ""
            stock_row[date] = round(temp_stock, 3)
            
        rows.append(usage_row)
        rows.append(stock_row)
    
    # データフレーム化
    df_result = pd.DataFrame(rows)
    
    # 列の並び順を整える
    cols = ['品番', '品名', '現在庫', '区分'] + list(dates)
    return df_result[cols]

# 他の関数は前回同様
def process_inventory(df):
    return df[~df['製造実績番号'].astype(str).contains('計')].fillna(0)

def process_receipts(df):
    return df.fillna(0)
