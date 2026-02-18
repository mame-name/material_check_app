import pandas as pd
import numpy as np
from datetime import datetime

# 引数に df_rec を追加
def create_pivot(df_req, df_inv, df_ord, df_rec):
    # 前処理などはそのまま維持
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    df_ord.columns = df_ord.columns.str.strip()
    # df_rec も必要に応じてストリップ
    df_rec.columns = df_rec.columns.str.strip()
    
    # --- 以下、これまでのロジックを維持 ---
    today = pd.Timestamp(datetime.now().date())
    tomorrow = today + pd.Timedelta(days=1)
    
    # 在庫取得
    df_inv['合計在庫数'] = pd.to_numeric(df_inv['合計在庫数'], errors='coerce').fillna(0)
    df_stock_master = df_inv.drop_duplicates(subset=['品番'], keep='last')[['品番', '合計在庫数']]
    current_stock_dict = df_stock_master.set_index('品番')['合計在庫数'].apply(lambda x: round(x, 3)).to_dict()

    # 要求量
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0)
    df_req['要求日'] = pd.to_datetime(df_req['要求日'], format='%y/%m/%d', errors='coerce')
    df_req = df_req.dropna(subset=['要求日'])

    # 発注リスト（明日以降）
    df_ord['発注数量'] = pd.to_numeric(df_ord['発注数量'], errors='coerce').fillna(0)
    df_ord['納期'] = pd.to_datetime(df_ord['納期'], format='%y/%m/%d', errors='coerce')
    df_ord = df_ord.dropna(subset=['納期'])
    df_ord_future = df_ord[df_ord['納期'] >= tomorrow].copy()

    # カレンダー作成（今日から）
    combined_dates = pd.concat([df_req['要求日'], df_ord['納期']])
    if len(combined_dates) > 0:
        max_date = combined_dates.max()
        all_dates = pd.date_range(start=today, end=max_date if max_date >= today else today, freq='D')
        
        pivot_req = df_req.pivot_table(index=['品番', '品名'], columns='要求日', values='基準単位数量', aggfunc='sum').fillna(0)
        pivot_ord = df_ord_future.pivot_table(index='品番', columns='納期', values='発注数量', aggfunc='sum').fillna(0)
        
        pivot_req = pivot_req.reindex(columns=all_dates, fill_value=0.0)
        pivot_ord = pivot_ord.reindex(columns=all_dates, fill_value=0.0)
    else:
        return pd.DataFrame()
    
    date_labels = [d.strftime('%y/%m/%d') for d in all_dates]
    pivot_req.columns = date_labels
    pivot_ord.columns = date_labels

    # 3段構築（ロジック変更なし）
    rows = []
    for (code, name), req_values in pivot_req.iterrows():
        initial_stock = current_stock_dict.get(code, 0.0)
        usage_row = {'品番': code, '品名': name, '現在庫': initial_stock, '区分': '要求量 (ー)'}
        order_row = {'品番': "", '品名': "", '現在庫': None, '区分': '納品数 (＋)'}
        stock_row = {'品番': "", '品名': "", '現在庫': None, '区分': '在庫残 (＝)'}
        temp_stock = initial_stock
        ord_values = pivot_ord.loc[code] if code in pivot_ord.index else None
        
        for date_label in date_labels:
            req_qty = round(float(req_values[date_label]), 3)
            rec_qty = round(float(ord_values[date_label]), 3) if ord_values is not None else 0.0
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
