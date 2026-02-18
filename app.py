import streamlit as st
import pandas as pd
from calc import create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")

# --- UIデザイン（2画面独立スクロール ＋ アップローダーの薄型化） ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* 左カラム：操作パネル（固定） */
    [data-testid="stColumn"]:nth-child(1) {
        position: sticky;
        top: 0;
        height: 100vh;
        overflow-y: auto;
        background-color: #ffffff;
        padding: 1.5rem; /* 余白を少し削る */
        border-right: 2px solid #e9ecef;
    }
    
    /* 右カラム：表示エリア（独立スクロール） */
    [data-testid="stColumn"]:nth-child(2) {
        height: 100vh;
        overflow-y: auto;
        padding: 2rem;
        background-color: #f8f9fa;
    }
    
    header {visibility: hidden;}
    #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}

    /* ★アップローダーを縦方向に薄くするCSS */
    [data-testid="stFileUploader"] {
        padding: 0 !important;
        margin-bottom: -10px; /* 下の隙間を詰める */
    }
    [data-testid="stFileUploader"] section {
        padding: 0.2rem 1rem !important; /* 内部のパディングを極限まで削る */
        min-height: 70px !important; /* 最小高さを抑える */
    }
    [data-testid="stFileUploader"] label {
        margin-bottom: 2px !important;
        font-size: 0.85rem !important; /* ラベル文字も少し小さく */
    }
    /* ドラッグ＆ドロップのテキスト部分を非表示（または薄く）して高さを抑える */
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none;
    }

    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("### 📁 データ読込")
    st.markdown("---")
    # label_visibility="visible" のままでもCSSで薄くなります
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 在庫一覧表", type=['xlsx', 'xls'], key="inv")
    file_ord = st.file_uploader("3. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.divider()
    st.caption("3つのファイルを読み込むと計算を開始します。")

with col2:
    st.markdown("<h1 style='text-align: center;'>原料在庫シミュレーション</h1>", unsafe_allow_html=True)
    st.markdown("---")

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
                height=1000,
                hide_index=True,
                column_config={
                    "品番": st.column_config.TextColumn("品番", pinned=True),
                    "品名": st.column_config.TextColumn("品名", pinned=True),
                }
            )
        except Exception as e:
            st.error(f"解析エラーが発生しました: {e}")
    else:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #d1d1d1;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
