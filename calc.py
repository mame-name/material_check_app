import pandas as pd
import numpy as np

def create_pivot(df_req, df_inv, df_ord):
    # 1. 前処理
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    df_ord.columns = df_ord.columns.str.strip()
    
    # 2. 現在庫取得 (各品番の最終行を参照)
    df_inv['合計在庫数'] = pd.to_numeric(df_inv['合計在庫数'], errors='coerce').fillna(0)
    df_stock_master = df_inv.drop_duplicates(subset=['品番'], keep='last')[['品番', '合計在庫数']]
    current_stock_dict = df_stock_master.set_index('品番')['合計在庫数'].apply(lambda x: round(x, 3)).to_dict()

    # 3. 要求量のピボット作成
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0)
    df_req['要求日'] = pd.to_datetime(df_req['要求日'], format='%y/%m/%d', errors='coerce')
    df_req = df_req.dropna(subset=['要求日'])
    pivot_req = df_req.pivot_table(index=['品番', '品名'], columns='要求日', values='基準単位数量', aggfunc='sum').fillna(0)

    # 4. 発注リスト（納品数）のピボット作成
    df_ord['発注数量'] = pd.to_numeric(df_ord['発注数量'], errors='coerce').fillna(0)
    df_ord['納期'] = pd.to_datetime(df_ord['納期'], format='%y/%m/%d', errors='coerce')
    df_ord = df_ord.dropna(subset=['納期'])
    # 品番と納期で集計（重複対応）
    pivot_ord = df_ord.pivot_table(index='品番', columns='納期', values='発注数量', aggfunc='sum').fillna(0)

    # 5. 横軸拡張 (要求日と納期の全期間をカバー)
    all_dates_idx = pd.to_datetime(pd.concat([df_req['要求日'], df_ord['納期']]).unique())
    if not all_dates_idx.empty:
        all_dates = pd.date_range(start=all_dates_idx.min(), end=all_dates_idx.max(), freq='D')
        pivot_req = pivot_req.reindex(columns=all_dates, fill_value=0.0)
        pivot_ord = pivot_ord.reindex(columns=all_dates, fill_value=0.0)
    
    date_labels = [d.strftime('%y/%m/%d') for d in pivot_req.columns]
    pivot_req.columns = date_labels
    pivot_ord.columns = date_labels

    # 6. 3段表示の構築
    rows = []
    for (code, name), req_values in pivot_req.iterrows():
        initial_stock = current_stock_dict.get(code, 0.0)
        
        # 各行の雛形（品番・品名は1段目のみ表示）
        usage_row = {'品番': code, '品名': name, '現在庫': initial_stock, '区分': '要求量 (ー)'}
        order_row = {'品番': "", '品名': "", '現在庫': None, '区分': '納品数 (＋)'}
        stock_row = {'品番': "", '品名': "", '現在庫': None, '区分': '在庫残 (＝)'}
        
        temp_stock = initial_stock
        ord_values = pivot_ord.loc[code] if code in pivot_ord.index else None
        
        for date_label in date_labels:
            req_qty = round(float(req_values[date_label]), 3)
            # 発注リストからの納品数
            rec_qty = round(float(ord_values[date_label]), 3) if ord_values is not None else 0.0
            
            # 在庫計算ロジック
            temp_stock = round(temp_stock - req_qty + rec_qty, 3)
            
            usage_row[date_label] = req_qty
            order_row[date_label] = rec_qty
            stock_row[date_label] = temp_stock
            
        rows.append(usage_row)
        rows.append(order_row)
        rows.append(stock_row)
    
    result_df = pd.DataFrame(rows)
    fixed_cols = ['品番', '品名', '現在庫', '区分']
    return result_df[fixed_cols + date_labels]
