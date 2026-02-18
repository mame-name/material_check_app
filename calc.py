import pandas as pd

def create_pivot(df):
    """
    縦軸：品番、品名
    横軸：要求日
    値：基準単位数量の合計
    ※合計行・列は含めない
    """
    # 列名の空白削除
    df.columns = df.columns.str.strip()
    
    # ピボットテーブル作成
    pivot = df.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum',
        margins=False  # 合計値を出さない設定
    ).fillna(0)
    
    # 見た目を整える（インデックスの品番・品名を通常の列に戻す）
    pivot = pivot.reset_index()
    
    return pivot

def process_inventory(df):
    df.columns = df.columns.str.strip()
    # 「【工程順計】」という文字が含まれる行を除外（合計値がいらないため）
    if '製造実績番号' in df.columns:
        df = df[~df['製造実績番号'].astype(str).contains('計')]
    return df.fillna(0)

def process_receipts(df):
    df.columns = df.columns.str.strip()
    return df.fillna(0)

def process_requirements(df):
    # app.pyで直接create_pivotを呼ぶため、ここは基本補正のみ
    df.columns = df.columns.str.strip()
    return df
