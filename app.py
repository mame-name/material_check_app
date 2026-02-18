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

with col2:
    st.header("📋 シミュレーション結果")
    
    if file_req and file_inv:
        try:
            # ヘッダー位置を正確に指定
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            
            # シミュレーション実行
            df_sim = process_files_and_create_sim(df_req, df_inv)
            
            # マイナスを赤字にするスタイル関数
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red'
                return None

            st.write("※2行目の「在庫残」がマイナスになると赤く表示されます。")
            # スタイルを適用して表示
            st.dataframe(
                df_sim.style.applymap(color_negative_red),
                use_container_width=True,
                height=600,
                hide_index=True
            )
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            st.info("Excelの列名（品番、品名、要求日、合計在庫数など）が正しいか確認してください。")
    else:
        st.info("左側で「所要量」と「在庫」の2つのファイルをアップロードしてください。")
