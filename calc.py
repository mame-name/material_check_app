import pandas as pd
import numpy as np

def create_pivot(df_req, df_inv):
    # 1. 前処理
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    
    # 2. 在庫取得 (各品番の先頭行から)
    df_inv['合計在庫数'] = pd.to_numeric(df_inv['合計在庫数'], errors='coerce').fillna(0)
    df_stock_master = df_inv.drop_duplicates(subset=['品番'], keep='first')[['品番', '合計在庫数']]
    current_stock_dict = df_stock_master.set_index('品番')['合計在庫数'].apply(lambda x: round(x, 3)).to_dict()

    # 3. 所要量のピボット作成
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0)
    df_req['要求日'] = pd.to_datetime(df_req['要求日'], format='%y/%m/%d', errors='coerce')
    df_req = df_req.dropna(subset=['要求日'])
    
    pivot = df_req.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum'
    ).fillna(0)

    # 4. 横軸拡張 (1日刻みカレンダー)
    if not pivot.columns.empty:
        all_dates = pd.date_range(start=pivot.columns.min(), end=pivot.columns.max(), freq='D')
        pivot = pivot.reindex(columns=all_dates, fill_value=0.0)
    
    date_labels = [d.strftime('%y/%m/%d') for d in pivot.columns]
    pivot.columns = date_labels

    # 5. 2段表示の構築
    rows = []
    
    for (code, name), req_values in pivot.iterrows():
        initial_stock = current_stock_dict.get(code, 0.0)
        
        # 1段目: 要求量
        usage_row = {
            '品番': code, 
            '品名': name, 
            '現在庫': initial_stock, 
            '区分': '要求量 (ー)'
        }
        
        # 2段目: 結合風（空白）
        stock_row = {
            '品番': None, 
            '品名': None, 
            '現在庫': None, 
            '区分': '在庫残 (＝)'
        }
        
        temp_stock = initial_stock
        for date_label in date_labels:
            req_qty = round(float(req_values[date_label]), 3)
            temp_stock = round(temp_stock - req_qty, 3)
            
            usage_row[date_label] = req_qty
            stock_row[date_label] = temp_stock
            
        rows.append(usage_row)
        rows.append(stock_row)
    
    result_df = pd.DataFrame(rows)
    fixed_cols = ['品番', '品名', '現在庫', '区分']
    final_cols = fixed_cols + date_labels
    
    return result_df[final_cols]

def process_receipts(df):
    df.columns = df.columns.str.strip()
    return df.fillna(0)
