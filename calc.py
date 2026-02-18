import streamlit as st
import pandas as pd
from calc import process_files_and_create_sim

# 画面幅を広く使う設定
st.set_page_config(layout="wide", page_title="在庫シミュレーション")

st.title("📉 在庫・所要量推移シミュレーション")

# 画面を2分割 (左: 操作パネル, 右: 結果表示)
col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 データ取り込み")
    st.info("Excelファイルをアップロードしてください。")
    
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 製造実績番号別在庫", type=['xlsx', 'xls'], key="inv")

with col2:
    st.header("📋 シミュレーション結果")
    
    if file_req and file_inv:
        try:
            # Excelの読み込み (ヘッダー位置をデータに合わせて調整)
            # 所要量: 4行目(index=3), 在庫: 5行目(index=4)
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            
            # 計算ロジック実行
            df_sim = process_files_and_create_sim(df_req, df_inv)
            
            # マイナス値を赤字にするスタイル関数
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            # 結果の表示
            st.write("💡 **在庫残 (＝)** の行がマイナスになると赤く表示されます。")
            st.dataframe(
                df_sim.style.applymap(color_negative_red),
                use_container_width=True,
                height=700,
                hide_index=True
            )
            
            # ダウンロード機能（CSV）
            csv = df_sim.to_csv(index=False).encode('utf_8_sig')
            st.download_button("結果をCSVで保存", csv, "stock_simulation.csv", "text/csv")

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            st.warning("Excelの形式（列名やヘッダー位置）が一致しているか確認してください。")
    else:
        st.info("左側のパネルから「所要量」と「在庫」の2つのファイルをアップロードしてください。")
