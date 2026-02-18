import streamlit as st
import pandas as pd
from calc import process_requirements, process_inventory, process_receipts, create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")
st.title("📦 生産管理・在庫管理システム")

col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 Excelファイル取り込み")
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 製造実績番号別在庫", type=['xlsx', 'xls'], key="inv")
    file_rec = st.file_uploader("3. 受入表", type=['xlsx', 'xls'], key="rec")

with col2:
    st.header("📋 データ表示・ソート")
    tab1, tab2, tab3 = st.tabs(["所要量集計表", "在庫(実績番号別)", "受入データ"])
    
    with tab1:
        if file_req:
            # header=3 は、実際のデータが4行目から始まっている場合に調整する数字です
            df_req = pd.read_excel(file_req, header=3) 
            df_req = process_requirements(df_req)
            
            # ピボットテーブルの作成
            st.subheader("🗓️ 日付別・品番別 所要量合計")
            df_pivot = create_pivot(df_req)
            st.dataframe(df_pivot, use_container_width=True)
            
            with st.expander("元の明細データを確認"):
                st.dataframe(df_req, use_container_width=True)
        else:
            st.info("「所要量一覧表」をアップロードしてください。")

    # 在庫・受入のタブは前回同様（省略可ですが構造は維持）
    with tab2:
        if file_inv:
            df_inv = pd.read_excel(file_inv, header=4)
            st.dataframe(process_inventory(df_inv), use_container_width=True)
    with tab3:
        if file_rec:
            df_rec = pd.read_excel(file_rec, header=2)
            st.dataframe(process_receipts(df_rec), use_container_width=True)
