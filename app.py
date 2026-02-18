import streamlit as st
import pandas as pd
from calc import process_requirements, process_inventory, process_receipts, create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")
st.title("📦 生産管理・在庫管理システム")

col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 Excelファイル取り込み")
    # 所要量一覧表: 4行目(index=3)がヘッダー
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    # 在庫一覧表: 5行目(index=4)がヘッダー
    file_inv = st.file_uploader("2. 製造実績番号別在庫", type=['xlsx', 'xls'], key="inv")
    # 受入表: 3行目(index=2)がヘッダー
    file_rec = st.file_uploader("3. 受入表", type=['xlsx', 'xls'], key="rec")

with col2:
    st.header("📋 データ表示・ソート")
    tab1, tab2, tab3 = st.tabs(["所要量集計表", "在庫(実績番号別)", "受入データ"])
    
    with tab1:
        if file_req:
            df_req = pd.read_excel(file_req, header=3) 
            # ピボットテーブルの表示（合計なし）
            df_pivot = create_pivot(df_req)
            st.subheader("🗓️ 品番別・要求日別 所要量")
            st.dataframe(df_pivot, use_container_width=True)
        else:
            st.info("「所要量一覧表」をアップロードしてください。")

    with tab2:
        if file_inv:
            df_inv = pd.read_excel(file_inv, header=4)
            st.dataframe(process_inventory(df_inv), use_container_width=True, hide_index=True)

    with tab3:
        if file_rec:
            df_rec = pd.read_excel(file_rec, header=2)
            st.dataframe(process_receipts(df_rec), use_container_width=True, hide_index=True)
