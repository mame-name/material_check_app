import pandas as pd

def process_files_and_create_sim(df_req, df_inv):
    # 列名の空白を削除
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    
    # 1. 在庫合計を抽出
    # 製造実績番号が「【工程順計】」となっている行に、その品番の合計在庫が入っています
    df_inv_total = df_inv[df_inv['製造実績番号'].astype(str).str.contains('【工程順計】', na=False)].copy()
    
    # 品番をキーにして合計在庫数を辞書化
    df_inv_total['合計在庫数'] = pd.to_numeric(df_inv_total['合計在庫数'], errors='coerce').fillna(0)
    current_stock = df_inv_total.set_index('品番')['合計在庫数'].to_dict()
    
    # 2. 所要量のピボット作成
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0)
    
    # 日付を昇順で並べるためにソート
    df_req['要求日'] = pd.to_datetime(df_req['要求日'], format='%y/%m/%d', errors='coerce')
    pivot_req = df_req.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum'
    ).fillna(0)
    
    # 3. シミュレーション計算
    rows = []
    # 日付列を文字列（YY/MM/DD）に戻してループ用にする
    dates = pivot_req.columns
    
    for (code, name), req_row in pivot_req.iterrows():
        # 在庫マスターから初期在庫を取得
        initial_stock = current_stock.get(code, 0)
        
        # 1行目: 使用量
        usage_row = {
            '品番': code, 
            '品名': name, 
            '現在庫': initial_stock, 
            '区分': '使用量 (ー)'
        }
        # 2行目: 在庫残
        stock_row = {
            '品番': code, 
            '品名': name, 
            '現在庫': "", 
            '区分': '在庫残 (＝)'
        }
        
        temp_stock = initial_stock
        for date in dates:
            usage = req_row[date]
            temp_stock -= usage
            
            # 日付の表示形式を整える
            date_str = date.strftime('%y/%m/%d')
            usage_row[date_str] = usage if usage != 0 else ""
            stock_row[date_str] = round(temp_stock, 3)
            
        rows.append(usage_row)
        rows.append(stock_row)
    
    # データフレーム化
    df_result = pd.DataFrame(rows)
    
    # 列の並びを整理
    date_cols = [d.strftime('%y/%m/%d') for d in dates]
    cols = ['品番', '品名', '現在庫', '区分'] + date_cols
    return df_result[cols]]
