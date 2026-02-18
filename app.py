import streamlit as st
import pandas as pd
from calc import create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")
st.title("📉 在庫・所要量推移シミュレーション")

col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 Excelファイル取り込み")
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 製造実績番号別在庫一覧表", type=['xlsx', 'xls'], key="inv")
    file_ord = st.file_uploader("3. 発注リスト", type=['xlsx', 'xls'], key="ord")
    # --- 新しく追加 ---
    file_rec = st.file_uploader("4. 受入表", type=['xlsx', 'xls'], key="rec")

with col2:
    st.header("📋 在庫推移シミュレーション")
    
    # 4つのファイルが揃ったら実行（まずは読み込みまで）
    if file_req and file_inv and file_ord and file_rec:
        try:
            # 各エクセルの読み込み
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            df_ord = pd.read_excel(file_ord, header=4)
            # 受入表の読み込み（ヘッダー行は適宜調整してください。ここでは例として0にしています）
            df_rec = pd.read_excel(file_rec, header=0)
            
            # ロジック側へ渡す（calc.pyの引数も後ほど合わせます）
            df_result = create_pivot(df_req, df_inv, df_ord, df_rec)
            
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            st.dataframe(
                df_result.style.applymap(color_negative_red).format(precision=3, na_rep=""),
                use_container_width=True,
                height=800,
                hide_index=True,
                column_config={
                    "品番": st.column_config.TextColumn("品番", pinned=True),
                    "品名": st.column_config.TextColumn("品名", pinned=True),
                }
            )
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
    else:
        st.info("左側の4つのファイルをすべてアップロードしてください。")
