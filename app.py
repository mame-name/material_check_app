import streamlit as st
import pandas as pd
from calc import process_requirements, process_inventory, process_receipts, create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")
st.title("📦 生産管理・在庫管理システム")

# 画面分割 (左: 3, 右: 7)
col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 Excelファイル取り込み")
    
    # 各ファイルのヘッダー位置に合わせて読み込み
    st.subheader("1. 所要量一覧表")
    file_req = st.file_uploader("Excelを選択 (所要量)", type=['xlsx', 'xls'], key="req")
    
    st.divider()
    
    st.subheader("2. 製造実績番号別在庫")
    file_inv = st.file_uploader("Excelを選択 (在庫)", type=['xlsx', 'xls'], key="inv")
    
    st.divider()
    
    st.subheader("3. 受入表")
    file_rec = st.file_uploader("Excelを選択 (受入)", type=['xlsx', 'xls'], key="rec")

with col2:
    st.header("📋 データ表示・ソート")
    
    tab1, tab2, tab3 = st.tabs(["所要量集計表", "在庫(実績番号別)", "受入データ"])
    
    with tab1:
        if file_req:
            # 4行目がヘッダー（index=3）
            df_req = pd.read_excel(file_req, header=3)
            # ピボットテーブルの表示
            st.subheader("🗓️ 品番別・要求日別 所要量")
            df_pivot = create_pivot(df_req)
            st.dataframe(df_pivot, use_container_width=True)
        else:
            st.info("「所要量一覧表」をアップロードしてください。")

    with tab2:
        if file_inv:
            # 5行目がヘッダー（index=4）
            df_inv = pd.read_excel(file_inv, header=4)
            df_inv = process_inventory(df_inv)
            st.dataframe(df_inv, use_container_width=True, hide_index=True)
        else:
            st.info("「在庫一覧表」をアップロードしてください。")

    with tab3:
        if file_rec:
            # 3行目がヘッダー（index=2）
            df_rec = pd.read_excel(file_rec, header=2)
            df_rec = process_receipts(df_rec)
            st.dataframe(df_rec, use_container_width=True, hide_index=True)
        else:
            st.info("「受入表」をアップロードしてください。")
