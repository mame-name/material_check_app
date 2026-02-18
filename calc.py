import pandas as pd

def process_requirements(df):
    # 列名の余計な空白を削除
    df.columns = df.columns.str.strip()
    # 完了区分が「未完了」のものだけに絞り込むなどの処理も可能
    return df.fillna(0)

def create_pivot(df):
    """
    縦軸：品番
    横軸：要求日
    値：基準単位数量の合計
    """
    # 1. 必要な列だけ抽出
    # ※実際の列名に合わせて適宜修正してください
    df_pivot = df.pivot_table(
        index=['品番', '品名'], 
        columns='要求日', 
        values='基準単位数量', 
        aggfunc='sum'
    ).fillna(0) # 予定がない日は0にする
    
    return df_pivot

def process_inventory(df):
    df.columns = df.columns.str.strip()
    # 【工程順計】などの不要な行を除去するロジックをここに入れると綺麗になります
    return df[~df['製造実績番号'].astype(str).contains('計')].fillna(0)

def process_receipts(df):
    df.columns = df.columns.str.strip()
    return df.fillna(0)
