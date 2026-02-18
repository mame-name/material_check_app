import streamlit as st
import pandas as pd
from calc import create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")

# --- 完全2画面独立スクロール & デザイン調整のCSS ---
st.markdown("""
    <style>
    /* 全体の背景色と余白調整 */
    .main {
        background-color: #f8f9fa;
    }
    
    /* 左カラム（操作パネル）の固定設定 */
    [data-testid="stColumn"]:nth-child(1) {
        position: sticky;
        top: 0;
        height: 100vh;
        overflow-y: auto;
        background-color: #ffffff;
        padding: 2rem;
        border-right: 2px solid #e9ecef;
    }
    
    /* 右カラム（表示エリア）の独立スクロール設定 */
    [data-testid="stColumn"]:nth-child(2) {
        height: 100vh;
        overflow-y: auto;
        padding: 2rem;
        background-color: #f8f9fa;
    }

    /* Streamlit標準のヘッダーを非表示にしてスペースを確保 */
    header {visibility: hidden;}
    #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 3]) # 比率を少し調整（左をスリムに）

with col1:
    st.subheader("📂 ファイル取り込み")
    st.divider()
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 在庫一覧表", type=['xlsx', 'xls'], key="inv")
    file_ord = st.file_uploader("3. 発注リスト", type=['xlsx', 'xls'], key="ord")
    
    st.caption("※3つのファイルをアップロードすると右側にシミュレーションが表示されます。")

with col2:
    # タイトルを右画面の最上部に配置
    st.title("📉 在庫・所要量推移シミュレーション")
    st.divider()
    
    if file_req and file_inv and file_ord:
        try:
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            df_ord = pd.read_excel(file_ord, header=4)
            
            df_result = create_pivot(df_req, df_inv, df_ord)
            
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            st.dataframe(
                df_result.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
                use_container_width=True,
                height=1200, # 表を大きく表示
                hide_index=True,
                column_config={
                    "品番": st.column_config.TextColumn("品番", pinned=True),
                    "品名": st.column_config.TextColumn("品名", pinned=True),
                }
            )
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
    else:
        st.info("左側のパネルからファイルをアップロードしてください。")
