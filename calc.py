import pandas as pd
import numpy as np
from datetime import datetime

def create_pivot(df_req, df_inv, df_ord):
    # 1. 前処理
    for df in [df_req, df_inv, df_ord]:
        df.columns = df.columns.str.strip()
    
    # 基準日：今日
    today = pd.Timestamp(datetime.now().date())
    
    # 2. 現在庫取得 (NaN排除)
    df_inv['合計在庫数'] = pd.to_numeric(df_inv['合計在庫数'], errors='coerce').fillna(0.0)
    df_stock_master = df_inv.drop_duplicates(subset=['品番'], keep='last')[['品番', '合計在庫数']]
    current_stock_dict = df_stock_master.set_index('品番')['合計在庫数'].apply(lambda x: round(float(x), 3)).to_dict()

    # 3. 要求量の集計 (今日以降をすべて保持)
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0.0)
    df_req['要求日'] = pd.to_datetime(df_req['要求日'], format='%y/%m/%d', errors='coerce')
    df_req = df_req.dropna(subset=['要求日'])
    # 今日以降の要求を抽出
    df_req_today_on = df_req[df_req['要求日'] >= today].copy()

    # 4. 発注リストの集計 (今日以降をすべて保持)
    df_ord['発注数量'] = pd.to_numeric(df_ord['発注数量'], errors='coerce').fillna(0.0)
    df_ord['納期'] = pd.to_datetime(df_ord['納期'], format='%y/%m/%d', errors='coerce')
    df_ord = df_ord.dropna(subset=['納期'])
    # 今日以降の納期を抽出
    df_ord_today_on = df_ord[df_ord['納期'] >= today].copy()

    # 5. 横軸（カレンダー）作成
    combined_dates = pd.concat([df_req_today_on['要求日'], df_ord_today_on['納期']])
    if len(combined_dates) > 0:
        max_date = combined_dates.max()
        # 今日 〜 データ上の最大日
        all_dates = pd.date_range(start=today, end=max_date if max_date >= today else today, freq='D')
        
        # ピボット作成
        pivot_req_raw = df_req_today_on.pivot_table(index=['品番', '品名'], columns='要求日', values='基準単位数量', aggfunc='sum').fillna(0.0)
        pivot_ord_raw = df_ord_today_on.pivot_table(index='品番', columns='納期', values='発注数量', aggfunc='sum').fillna(0.0)
        
        # カレンダーに再配置 (fillnaでNaNを徹底ガード)
        pivot_req = pivot_req_raw.reindex(columns=all_dates, fill_value=0.0).fillna(0.0)
        pivot_ord = pivot_ord_raw.reindex(columns=all_dates, fill_value=0.0).fillna(0.0)
    else:
        return pd.DataFrame()
    
    date_labels = [d.strftime('%y/%m/%d') for d in all_dates]
    pivot_req.columns = date_labels
    pivot_ord.columns = date_labels

    # 6. 3段表示データの構築
    rows = []
    for (code, name), req_values in pivot_req.iterrows():
        # 在庫表になければ0.0
        initial_stock = float(current_stock_dict.get(code, 0.0))
        
        usage_row = {'品番': code, '品名': name, '現在庫': initial_stock, '区分': '要求量 (ー)'}
        deliv_row = {'品番': "", '品名': "", '現在庫': 0.0, '区分': '納品数 (＋)'}
        stock_row = {'品番': "", '品名': "", '現在庫': 0.0, '区分': '在庫残 (＝)'}
        
        temp_stock = initial_stock
        ord_values = pivot_ord.loc[code] if code in pivot_ord.index else None
        
        for date_label in date_labels:
            r_qty = round(float(req_values[date_label]), 3)
            o_qty = round(float(ord_values[date_label]), 3) if ord_values is not None else 0.0
            
            # 在庫計算：前日残 - 当日要求 + 当日納品
            temp_stock = round(temp_stock - r_qty + o_qty, 3)
            
            usage_row[date_label] = r_qty
            deliv_row[date_label] = o_qty
            stock_row[date_label] = temp_stock
            
        rows.append(usage_row)
        rows.append(deliv_row)
        rows.append(stock_row)
    
    result_df = pd.DataFrame(rows).fillna(0.0)
    fixed_cols = ['品番', '品名', '現在庫', '区分']
    return result_df[fixed_cols + date_labels]
