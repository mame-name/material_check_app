import pandas as pd
import numpy as np
from datetime import datetime

def create_pivot(df_req, df_inv, df_ord, df_rec):
    # 1. 前処理：列名の余計な空白を削除
    for df in [df_req, df_inv, df_ord, df_rec]:
        df.columns = df.columns.str.strip()
    
    # 基準日の設定
    today = pd.Timestamp(datetime.now().date())
    tomorrow = today + pd.Timedelta(days=1)
    
    # 2. 現在庫取得 (各品番の最終行を参照)
    df_inv['合計在庫数'] = pd.to_numeric(df_inv['合計在庫数'], errors='coerce').fillna(0.0)
    df_stock_master = df_inv.drop_duplicates(subset=['品番'], keep='last')[['品番', '合計在庫数']]
    # fillna(0.0) を追加して辞書作成時のNoneを排除
    current_stock_dict = df_stock_master.set_index('品番')['合計在庫数'].apply(lambda x: round(float(x), 3)).to_dict()

    # 3. 要求量の集計
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0.0)
    df_req['要求日'] = pd.to_datetime(df_req['要求日'], format='%y/%m/%d', errors='coerce')
    df_req = df_req.dropna(subset=['要求日'])

    # 4. 発注リストの集計 (明日以降分のみ)
    df_ord['発注数量'] = pd.to_numeric(df_ord['発注数量'], errors='coerce').fillna(0.0)
    df_ord['納期'] = pd.to_datetime(df_ord['納期'], format='%y/%m/%d', errors='coerce')
    df_ord = df_ord.dropna(subset=['納期'])
    df_ord_future = df_ord[df_ord['納期'] >= tomorrow].copy()
    pivot_ord = df_ord_future.pivot_table(index='品番', columns='納期', values='発注数量', aggfunc='sum').fillna(0.0)

    # 5. 受入表の集計 (本日分など)
    df_rec['数量'] = pd.to_numeric(df_rec['数量'], errors='coerce').fillna(0.0)
    df_rec['納期'] = pd.to_datetime(df_rec['納期'], format='%y/%m/%d', errors='coerce')
    df_rec = df_rec.dropna(subset=['納期', '品番'])
    pivot_rec = df_rec.pivot_table(index='品番', columns='納期', values='数量', aggfunc='sum').fillna(0.0)

    # 6. 横軸（カレンダー）拡張：今日以降を表示
    combined_dates = pd.concat([df_req['要求日'], df_ord['納期'], df_rec['納期']])
    if len(combined_dates) > 0:
        max_date = combined_dates.max()
        all_dates = pd.date_range(start=today, end=max_date if max_date >= today else today, freq='D')
        
        # 要求量ピボット
        pivot_req_base = df_req.pivot_table(index=['品番', '品名'], columns='要求日', values='基準単位数量', aggfunc='sum').fillna(0.0)
        
        # カレンダーに合わせて再構成
        pivot_req = pivot_req_base.reindex(columns=all_dates, fill_value=0.0)
        pivot_ord_aligned = pivot_ord.reindex(columns=all_dates, fill_value=0.0)
        pivot_rec_aligned = pivot_rec.reindex(columns=all_dates, fill_value=0.0)
        
        # 納品スケジュールを一本化 (受入 + 発注予定)
        # reindex しているので欠損値NaNが発生するため、再度fillna(0.0)を適用
        pivot_delivery = (pivot_rec_aligned.fillna(0.0) + pivot_ord_aligned.fillna(0.0)).fillna(0.0)
    else:
        return pd.DataFrame()
    
    date_labels = [d.strftime('%y/%m/%d') for d in all_dates]
    pivot_req.columns = date_labels
    pivot_delivery.columns = date_labels

    # 7. 3段表示データの構築
    rows = []
    for (code, name), req_values in pivot_req.iterrows():
        # 在庫表にない品番は 0.0 とする
        initial_stock = float(current_stock_dict.get(code, 0.0))
        
        # 行のテンプレート (数値が期待される場所には 0.0 を、文字列の場所には "" を)
        usage_row = {'品番': code, '品名': name, '現在庫': initial_stock, '区分': '要求量 (ー)'}
        deliv_row = {'品番': "", '品名': "", '現在庫': 0.0, '区分': '納品数 (＋)'}
        stock_row = {'品番': "", '品名': "", '現在庫': 0.0, '区分': '在庫残 (＝)'}
        
        temp_stock = initial_stock
        deliv_values = pivot_delivery.loc[code] if code in pivot_delivery.index else None
        
        for date_label in date_labels:
            # 確実に数値化
            req_qty = round(float(req_values[date_label]), 3)
            rec_qty = round(float(deliv_values[date_label]), 3) if deliv_values is not None else 0.0
            
            # 在庫計算
            temp_stock = round(temp_stock - req_qty + rec_qty, 3)
            
            usage_row[date_label] = req_qty
            deliv_row[date_label] = rec_qty
            stock_row[date_label] = temp_stock
            
        rows.append(usage_row)
        rows.append(deliv_row)
        rows.append(stock_row)
    
    result_df = pd.DataFrame(rows)
    # 最終的なDataFrameのNaNを空文字または0に置換（念のためのガード）
    result_df = result_df.replace({np.nan: 0.0})
    
    fixed_cols = ['品番', '品名', '現在庫', '区分']
    return result_df[fixed_cols + date_labels]
