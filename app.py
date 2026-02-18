import streamlit as st
import pandas as pd
from calc import process_data

st.set_page_config(layout="wide")
st.title("📊 データベース管理・並べ替えアプリ")

# 画面を2分割 (左: 3, 右: 7 の比率)
col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 データ取り込み")
    uploaded_file = st.file_uploader("CSVファイルを選択してください", type='csv')
    
    if uploaded_file:
        # データの読み込み
        df = pd.read_csv(uploaded_file)
        st.success("ファイルを読み込みました！")
        
        # calc.pyで計算処理が必要な場合はここで実行
        df = process_data(df)

with col2:
    st.header("📋 データ一覧")
    if uploaded_file:
        # st.dataframe を使うと、ユーザーが列名をクリックしてソート可能になります
        st.write("列名をクリックすると昇順/降順に並べ替えができます。")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 簡易的な集計情報の表示
        st.info(f"現在の表示件数: {len(df)} 件")
    else:
        st.warning("左側のパネルからデータをアップロードしてください。")
