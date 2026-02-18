import streamlit as st
import pandas as pd
from calc import create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")

# --- UIデザイン（アップローダー薄型化・独立スクロール） ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stColumn"]:nth-child(1) {
        position: sticky; top: 0; height: 100vh; overflow-y: auto;
        background-color: #ffffff; padding: 2rem; border-right: 2px solid #e9ecef;
    }
    [data-testid="stColumn"]:nth-child(2) {
        height: 100vh; overflow-y: auto; padding: 2rem; background-color: #f8f9fa;
    }
    header {visibility: hidden;}
    #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
    .stFileUploader { border: 1px solid #e6e9ef; border-radius: 10px; padding: 5px; }
    [data-testid="stFileUploaderSmallNumber"] { display: none !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploader"] section { padding: 0px 10px !important; min-height: 50px !important; }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 3])

# --- データ読み込み（セッション管理） ---
with col1:
    st.markdown("##### 📁 データ読込")
    file_req = st.file_uploader("1. 所要量一覧表を選択", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 在庫一覧表を選択", type=['xlsx', 'xls'], key="inv")
    file_ord = st.file_uploader("3. 発注リストを選択", type=['xlsx', 'xls'], key="ord")
    
    st.divider()
    
    # 選択された製品コードを格納する変数
    selected_product = "全表示"

    if file_req:
        try:
            # G列の製品コードをリスト化するための読み込み
            df_req_raw = pd.read_excel(file_req, header=3)
            df_req_raw.columns = df_req_raw.columns.str.strip()
            col_g_name = df_req_raw.columns[6]
            
            # G列を6桁文字列に変換して重複排除
            product_list = df_req_raw[col_g_name].dropna().apply(
                lambda x: str(int(float(x))).zfill(6) if str(x).replace('.','',1).isdigit() else str(x)
            ).unique().tolist()
            product_list.sort()
            
            # プルダウンの作成
            selected_product = st.selectbox(
                "🔍 製品コードで絞り込み",
                options=["全表示"] + product_list,
                index=0
            )
        except:
            st.error("所要量一覧表の解析に失敗しました。")

    st.divider()
    st.caption("3つのファイルを読み込むと計算を開始します。")

with col2:
    st.markdown("<h1 style='text-align: center;'>原料在庫シミュレーション</h1>", unsafe_allow_html=True)
    st.markdown("---")

    if file_req and file_inv and file_ord:
        try:
            # 計算用の読み込み
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            df_ord = pd.read_excel(file_ord, header=4)
            df_req.columns = df_req.columns.str.strip()
            
            # G列の正規化（0埋め）
            col_g_name = df_req.columns[6]
            df_req[col_g_name] = df_req[col_g_name].apply(
                lambda x: str(int(float(x))).zfill(6) if pd.notnull(x) and str(x).replace('.','',1).isdigit() else str(x)
            )

            # 計算実行
            df_result = create_pivot(df_req, df_inv, df_ord)
            display_df = df_result

            # プルダウンが「全表示」以外ならフィルタリング
            if selected_product != "全表示":
                col_c_name = df_req.columns[2] # C列（品番）
                matched_materials = df_req[df_req[col_g_name] == selected_product][col_c_name].unique()
                display_df = df_result[df_result['品番'].isin(matched_materials)]

            # スタイル定義
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            if not display_df.empty:
                st.dataframe(
                    display_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
                    use_container_width=True,
                    height=1000,
                    hide_index=True,
                    column_config={
                        "品番": st.column_config.TextColumn("品番", pinned=True),
                        "品名": st.column_config.TextColumn("品名", pinned=True),
                    }
                )
            else:
                st.info("該当するデータがありません。")
            
        except Exception as e:
            st.error(f"解析エラーが発生しました: {e}")
    else:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #d1d1d1;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
