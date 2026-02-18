import pandas as pd

def process_files_and_create_sim(df_req, df_inv):
    # 列名の空白を削除
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    
    # 1. 現在の在庫合計を算出
    # 工程順計の行を除外し、品番ごとに合計在庫数を集計
    df_inv_clean = df_inv[~df_inv['製造実績番号'].astype(str).contains('計')].copy()
    # 数値列として強制変換（エラー回避）
    df_inv_clean['合計在庫数'] = pd.to_numeric(df_inv_clean['合計在庫数'], errors='coerce').fillna(0)
    current_stock = df_inv_clean.groupby('品番')['合計在庫数'].sum().to_dict()
    
    # 2. 所要量のピボット作成
    # 基準単位数量を数値化
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0)
    
    pivot_req = df_req.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum'
    ).fillna(0)
    
    # 3. シミュレーション計算
    rows = []
    dates = pivot_req.columns
    
    for (code, name), req_row in pivot_req.iterrows():
        # 初期在庫を取得
        initial_stock = current_stock.get(code, 0)
        
        # 1行目: 使用量行
        usage_row = {'品番': code, '品名': name, '区分': '使用量 (ー)', '現在庫': initial_stock}
        # 2行目: 在庫残行
        stock_row = {'品番': code, '品名': name, '区分': '在庫残 (＝)', '現在庫': ""}
        
        temp_stock = initial_stock
        for date in dates:
            usage = req_row[date]
            temp_stock -= usage
            
            # 使用量は0なら非表示、在庫残は常に表示
            usage_row[date] = usage if usage != 0 else ""
            stock_row[date] = round(temp_stock, 3)
            
        rows.append(usage_row)
        rows.append(stock_row)
    
    # データフレーム化
    df_result = pd.DataFrame(rows)
    
    # 列の並び順（品番, 品名, 現在庫, 区分, 日付...）
    cols = ['品番', '品名', '現在庫', '区分'] + list(dates)
    return df_result[cols]
