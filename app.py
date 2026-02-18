import streamlit as st
import pandas as pd
from calc import process_receipts, create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")
st.title("📦 生産管理・在庫管理システム")

col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 Excelファイル取り込み")
    
    st.subheader("1. 所要量一覧表")
    file_req = st.file_uploader("Excelを選択 (所要量)", type=['xlsx', 'xls'], key="req")
    
    st.divider()
    
    st.subheader("2. 製造実績番号別在庫一覧表")
    file_inv = st.file_uploader("Excelを選択 (在庫)", type=['xlsx', 'xls'], key="inv")
    
    st.divider()
    
    st.subheader("3. 受入表")
    file_rec = st.file_uploader("Excelを選択 (受入)", type=['xlsx', 'xls'], key="rec")

with col2:
    st.header("📋 在庫推移シミュレーション")
    
    if file_req and file_inv:
        try:
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            
            # 2段表示のデータを作成
            df_result = create_pivot(df_req, df_inv)
            
            # マイナス値を赤字にするスタイル
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            st.dataframe(
                df_result.style.applymap(color_negative_red),
                use_container_width=True,
                height=700,
                hide_index=True
            )
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
    else:
        st.info("左側で「所要量」と「在庫」の2つのファイルをアップロードしてください。")
