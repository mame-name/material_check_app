import pandas as pd

def create_pivot(df_req, df_inv):
    # 1. 前処理
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    
    # 2. 在庫取得 (指示通り、各品番の先頭行から合計在庫数を取得)
    df_inv['合計在庫数'] = pd.to_numeric(df_inv['合計在庫数'], errors='coerce').fillna(0)
    df_stock_master = df_inv.drop_duplicates(subset=['品番'], keep='first')[['品番', '合計在庫数']]
    current_stock_dict = df_stock_master.set_index('品番')['合計在庫数'].to_dict()

    # 3. 所要量のピボット作成
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0)
    # 日付を綺麗に並べるための処理
    df_req['要求日'] = pd.to_datetime(df_req['要求日'], errors='coerce').dt.strftime('%y/%m/%d')
    
    pivot = df_req.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum'
    ).fillna(0)
    
    # 4. 2段表示の構築
    rows = []
    dates = pivot.columns.tolist()
    
    for (code, name), req_values in pivot.iterrows():
        # この品番の初期在庫
        initial_stock = current_stock_dict.get(code, 0)
        
        # --- 1段目: 要求量行 ---
        usage_row = {
            '品番': code,
            '品名': name,
            '現在庫': initial_stock,
            '区分': '要求量 (ー)'
        }
        # --- 2段目: 在庫残行 ---
        stock_row = {
            '品番': code,
            '品名': name,
            '現在庫': "", # 見やすくするため空欄
            '区分': '在庫残 (＝)'
        }
        
        # 日付ごとの計算
        temp_stock = initial_stock
        for date in dates:
            req_qty = req_values[date]
            temp_stock -= req_qty  # 在庫残を更新
            
            usage_row[date] = req_qty if req_qty != 0 else ""
            stock_row[date] = round(temp_stock, 3)
            
        rows.append(usage_row)
        rows.append(stock_row)
    
    # データフレーム化
    result_df = pd.DataFrame(rows)
    
    # 列の順序整理
    fixed_cols = ['品番', '品名', '現在庫', '区分']
    final_cols = fixed_cols + dates
    
    return result_df[final_cols]

def process_receipts(df):
    df.columns = df.columns.str.strip()
    return df.fillna(0)
