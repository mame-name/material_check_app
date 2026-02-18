import streamlit as st
import pandas as pd
from calc import process_requirements, process_inventory, process_receipts

st.set_page_config(layout="wide", page_title="生産管理データ統合")
st.title("📦 生産管理・在庫管理システム")

# 画面分割 (左: 3, 右: 7)
col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 ファイル取り込み")
    
    # ① 所要量一覧表
    st.subheader("1. 所要量一覧表")
    file_req = st.file_uploader("CSVを選択", type='csv', key="req")
    
    st.divider() # 区切り線
    
    # ② 製造実績番号別在庫一覧表
    st.subheader("2. 製造実績番号別在庫")
    file_inv = st.file_uploader("CSVを選択", type='csv', key="inv")
    
    st.divider()
    
    # ③ 受入表
    st.subheader("3. 受入表")
    file_rec = st.file_uploader("CSVを選択", type='csv', key="rec")

with col2:
    st.header("📋 データ表示・ソート")
    
    # タブを作成して表示を整理
    tab1, tab2, tab3 = st.tabs(["所要量データ", "在庫(実績番号別)", "受入データ"])
    
    with tab1:
        if file_req:
            df_req = pd.read_csv(file_req)
            df_req = process_requirements(df_req)
            st.dataframe(df_req, use_container_width=True, hide_index=True)
        else:
            st.info("左側から「所要量一覧表」をアップロードしてください。")

    with tab2:
        if file_inv:
            df_inv = pd.read_csv(file_inv)
            df_inv = process_inventory(df_inv)
            st.dataframe(df_inv, use_container_width=True, hide_index=True)
        else:
            st.info("左側から「在庫一覧表」をアップロードしてください。")

    with tab3:
        if file_rec:
            df_rec = pd.read_csv(file_rec)
            df_rec = process_receipts(df_rec)
            st.dataframe(df_rec, use_container_width=True, hide_index=True)
        else:
            st.info("左側から「受入表」をアップロードしてください。")
