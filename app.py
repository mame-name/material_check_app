import streamlit as st
import pandas as pd
from calc import process_receipts, create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")
st.title("📉 在庫・所要量推移シミュレーション")

# --- CSSで左側の列を固定 ---
st.markdown("""
    <style>
    /* データフレームの特定列を固定するカスタムCSS */
    [data-testid="stTable"] {
        overflow: auto;
    }
    /* 品番、品名、現在庫、区分（1〜4列目）を固定 */
    /* ※Streamlitのバージョンやブラウザにより挙動が変わる場合があります */
    thead tr th:nth-child(1), tbody tr td:nth-child(1) { position: sticky; left: 0; background-color: white; z-index: 3; }
    thead tr th:nth-child(2), tbody tr td:nth-child(2) { position: sticky; left: 100px; background-color: white; z-index: 3; }
    thead tr th:nth-child(3), tbody tr td:nth-child(3) { position: sticky; left: 250px; background-color: white; z-index: 3; }
    thead tr th:nth-child(4), tbody tr td:nth-child(4) { position: sticky; left: 350px; background-color: white; z-index: 3; }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([3, 7])

with col1:
    st.header("📂 Excelファイル取り込み")
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 製造実績番号別在庫一覧表", type=['xlsx', 'xls'], key="inv")
    file_rec = st.file_uploader("3. 受入表", type=['xlsx', 'xls'], key="rec")

with col2:
    st.header("📋 在庫推移シミュレーション")
    
    if file_req and file_inv:
        try:
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            
            df_result = create_pivot(df_req, df_inv)
            
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            # 表示設定
            # hide_index=True にすることで、余計なindex列を消して品番を左端にします
            st.dataframe(
                df_result.style.applymap(color_negative_red).format(precision=3, na_rep=""),
                use_container_width=True,
                height=750,
                hide_index=True
            )
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
    else:
        st.info("左側で「所要量」と「在庫」をアップロードしてください。")
