import pandas as pd

def create_pivot(df):
    """
    縦軸：品番、品名
    横軸：要求日
    値：基準単位数量の合計
    """
    # 列名の前後の空白を削除
    df.columns = df.columns.str.strip()
    
    # 基準単位数量を数値に変換
    df['基準単位数量'] = pd.to_numeric(df['基準単位数量'], errors='coerce').fillna(0)
    
    # ピボットテーブル作成
    pivot = df.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum',
        margins=False  # 合計値（All）を出さない
    ).fillna(0)
    
    # インデックス（品番・品名）を列に戻す
    pivot = pivot.reset_index()
    
    return pivot

def process_inventory(df):
    """在庫一覧表の加工"""
    df.columns = df.columns.str.strip()
    # 合計行などを除外したい場合はここでフィルタリング
    return df.fillna(0)

def process_receipts(df):
    """受入表の加工"""
    df.columns = df.columns.str.strip()
    return df.fillna(0)

def process_requirements(df):
    """所要量一覧表の基本加工"""
    df.columns = df.columns.str.strip()
    return df
