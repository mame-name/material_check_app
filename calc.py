import pandas as pd

def create_pivot(df_req, df_inv):
    # 列名の空白削除
    df_req.columns = df_req.columns.str.strip()
    df_inv.columns = df_inv.columns.str.strip()
    
    # 1. 在庫データの処理: 各品番の「先頭行」の値を取得
    # 合計在庫数を数値に変換
    df_inv['合計在庫数'] = pd.to_numeric(df_inv['合計在庫数'], errors='coerce').fillna(0)
    # 品番ごとの最初の行だけを抽出（これが「本題」の条件）
    df_inventory_first = df_inv.drop_duplicates(subset=['品番'], keep='first')
    df_stock_master = df_inventory_first[['品番', '合計在庫数']].rename(columns={'合計在庫数': '現在庫'})

    # 2. 所要量データの処理
    df_req['基準単位数量'] = pd.to_numeric(df_req['基準単位数量'], errors='coerce').fillna(0)
    
    # ピボットテーブル作成
    pivot = df_req.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum',
        margins=False
    ).fillna(0).reset_index()
    
    # 3. 在庫データを左側に結合 (品番をキーにする)
    result = pd.merge(df_stock_master, pivot, on='品番', how='right')
    
    # 列の並びを調整 (品番, 品名, 現在庫, 日付...)
    cols = result.columns.tolist()
    fixed_cols = ['品番', '品名', '現在庫']
    # 日付列などを抽出
    date_cols = [c for c in cols if c not in fixed_cols]
    
    # 最終的な列構成
    result = result[fixed_cols + date_cols]
    
    return result.fillna(0)

def process_receipts(df):
    """受入表の列名クレンジング"""
    df.columns = df.columns.str.strip()
    return df.fillna(0)
