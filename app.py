import streamlit as st
import pandas as pd
import time
from calc import create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")

# --- UIデザイン用のカスタムCSS ---
st.markdown("""
    <style>
    /* 背景とフォント調整 */
    .main { background-color: #f8f9fa; }
    
    /* 左カラム（操作パネル） */
    [data-testid="stColumn"]:nth-child(1) {
        position: sticky;
        top: 0;
        height: 100vh;
        overflow-y: auto;
        background-color: #ffffff;
        padding: 2rem;
        border-right: 2px solid #e9ecef;
    }
    
    /* 右カラム（表示エリア） */
    [data-testid="stColumn"]:nth-child(2) {
        height: 100vh;
        overflow-y: auto;
        padding: 2rem;
        background-color: #f8f9fa;
    }

    /* ヘッダー周りの余白排除 */
    header {visibility: hidden;}
    #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
    
    /* カード風のデザイン */
    .stFileUploader {
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("### 📁 データ読込")
    st.markdown("---")
    
    file_req = st.file_uploader("1. 所要量一覧表を選択", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 在庫一覧表を選択", type=['xlsx', 'xls'], key="inv")
    file_ord = st.file_uploader("3. 発注リストを選択", type=['xlsx', 'xls'], key="ord")
    
    st.divider()
    st.caption("🤖 **Usage Tip** \n3つのファイルを読み込むと、AI（計算ロジック）が即座に在庫推移を解析します。")

with col2:
    # --- ヘッダー部分（UI参照） ---
    st.markdown("<h1 style='text-align: center;'>Intelligent Simulator<br>📉 📊 📈 在庫推移確認 📈 📊 📉</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>過去の在庫と未来の所要量を解析し、最適な在庫推移をシミュレーションします</p>", unsafe_allow_html=True)
    st.markdown("---")

    if file_req and file_inv and file_ord:
        try:
            # 解析中の演出
            with st.status("🧠 データを解析してシミュレーションを生成中...", expanded=False) as status:
                df_req = pd.read_excel(file_req, header=3)
                df_inv = pd.read_excel(file_inv, header=4)
                df_ord = pd.read_excel(file_ord, header=4)
                
                df_result = create_pivot(df_req, df_inv, df_ord)
                status.update(label="✅ 解析完了", state="complete")
            
            # 結果表示
            st.subheader("🔮 在庫推移シミュレーション結果")
            
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            st.dataframe(
                df_result.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
                use_container_width=True,
                height=1000,
                hide_index=True,
                column_config={
                    "品番": st.column_config.TextColumn("品番", pinned=True),
                    "品名": st.column_config.TextColumn("品名", pinned=True),
                }
            )
            
        except Exception as e:
            st.error(f"💀 解析エラーが発生しました: {e}")
    else:
        # 待機画面の演出
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #d1d1d1;'>📂 📂 📂</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #d1d1d1;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
