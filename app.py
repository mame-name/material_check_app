import pandas as pd

def process_files_and_create_sim(df_req, df_inv):
    # 列名の前後の空白を削除
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    
    # --- 1. 現在庫の取得 ---
    # 「製造実績番号」列が「【工程順計】」となっている行に合計在庫がある
    # シリーズに対して .str.contains を使う (エラー回避)
    mask = df_inv['製造実績番号'].astype(str).str.contains('【工程順計】', na=False)
    df_inv_totals = df_inv[mask].copy()
    
    # 在庫数を数値に変換
    df_inv_totals['合計在庫数'] = pd.to_numeric(df_inv_totals['合計在庫数'], errors='coerce').fillna(0)
    
    # 品番をキーにした在庫辞書を作成
    current_stock_dict = df_inv_totals.set_index('品番')['合計在庫数'].to_dict()

    # --- 2. 所要量の集計 (ピボット) ---
    # 数値変換と日付変換
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0)
    df_req['要求日'] = pd.to_datetime(df_req['要求日'], format='%y/%m/%d', errors='coerce')
    
    # 欠損日付を除外してピボット作成
    pivot_req = df_req.dropna(subset=['要求日']).pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum'
    ).fillna(0)

    # --- 3. 2行構成のシミュレーション表作成 ---
    rows = []
    dates = pivot_req.columns # 要求日のリスト（昇順）
    
    for (code, name), req_row in pivot_req.iterrows():
        # 在庫辞書からこの品番の在庫を取得
        initial_stock = current_stock_dict.get(code, 0)
        
        # 1行目: 使用量 (ー) 行のデータ準備
        usage_row = {
            '品番': code, 
            '品名': name, 
            '現在庫': initial_stock, 
            '区分': '使用量 (ー)'
        }
        
        # 2行目: 在庫残 (＝) 行のデータ準備
        stock_row = {
            '品番': code, 
            '品名': name, 
            '現在庫': "", # 見やすくするため空欄
            '区分': '在庫残 (＝)'
        }
        
        # 日付ごとに計算
        temp_stock = initial_stock
        for date in dates:
            usage = req_row[date]
            temp_stock -= usage # 前日在庫 - 今日の使用量
            
            # 日付の列名（YY/MM/DD形式）
            date_col = date.strftime('%y/%m/%d')
            
            usage_row[date_col] = usage if usage != 0 else ""
            stock_row[date_col] = round(temp_stock, 3)
            
        rows.append(usage_row)
        rows.append(stock_row)
    
    # 新しいデータフレームを作成
    df_result = pd.DataFrame(rows)
    
    # 表示順序を固定（品番, 品名, 現在庫, 区分, 日付...）
    date_cols = [d.strftime('%y/%m/%d') for d in dates]
    final_cols = ['品番', '品名', '現在庫', '区分'] + date_cols
    
    return df_result[final_cols]
