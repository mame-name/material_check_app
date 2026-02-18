import streamlit as st
import pandas as pd
from calc import process_files_and_create_sim

st.set_page_config(layout="wide", page_title="在庫シミュレーション")
st.title("📉 在庫・所要量推移シミュレーション")

col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 データ取り込み")
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 製造実績番号別在庫", type=['xlsx', 'xls'], key="inv")
    file_rec = st.file_uploader("3. 受入表", type=['xlsx', 'xls'], key="rec")

with col2:
    st.header("📋 シミュレーション結果")
    
    if file_req and file_inv:
        # データの読み込み
        df_req = pd.read_excel(file_req, header=3)
        df_inv = pd.read_excel(file_inv, header=4)
        
        # シミュレーション実行
        df_sim = process_files_and_create_sim(df_req, df_inv)
        
        # スタイル適用（マイナスを赤文字にする）
        def color_negative_red(val):
            if isinstance(val, (int, float)) and val < 0:
                return 'color: red'
            return ''

        # 表示設定
        st.write("各品番の2行目（在庫残）がマイナスになると赤く表示されます。")
        st.dataframe(
            df_sim.style.applymap(color_negative_red),
            use_container_width=True,
            height=600
        )
    else:
        st.info("左側で「所要量」と「在庫」のファイルをアップロードしてください。")
