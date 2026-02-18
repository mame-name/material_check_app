import streamlit as st
import pandas as pd
from calc import create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")

# --- UIデザイン（変更なし） ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stColumn"]:nth-child(1) {
        position: sticky;
        top: 0;
        height: 100vh;
        overflow-y: auto;
        background-color: #ffffff;
        padding: 2rem;
        border-right: 2px solid #e9ecef;
    }
    [data-testid="stColumn"]:nth-child(2) {
        height: 100vh;
        overflow-y: auto;
        padding: 2rem;
        background-color: #f8f9fa;
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

with col1:
    st.markdown("##### 📁 データ読込")
    file_req = st.file_uploader("1. 所要量一覧表を選択", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 在庫一覧表を選択", type=['xlsx', 'xls'], key="inv")
    file_ord = st.file_uploader("3. 発注リストを選択", type=['xlsx', 'xls'], key="ord")
    
    st.divider()
    # 入力された製品コードも6桁で扱う
    target_product_code = st.text_input("🔍 絞り込み製品コード", placeholder="例: 001006")
    
    st.divider()
    st.caption("3つのファイルを読み込むと計算を開始します。")

with col2:
    st.markdown("<h1 style='text-align: center;'>原料在庫シミュレーション</h1>", unsafe_allow_html=True)
    st.markdown("---")

    if file_req and file_inv and file_ord:
        try:
            # データの読み込み
            # 所要量一覧表の全列を一旦読み込み
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            df_ord = pd.read_excel(file_ord, header=4)

            # 列名のクリーニング（余計な空白を消す）
            df_req.columns = df_req.columns.str.strip()
            
            # --- G列の値を6桁の文字列に変換する処理 ---
            # G列(index 6)を特定し、数値を6桁（001006形式）に変換
            col_g_name = df_req.columns[6]
            df_req[col_g_name] = df_req[col_g_name].apply(lambda x: str(int(float(x))).zfill(6) if pd.notnull(x) and str(x).replace('.','',1).isdigit() else str(x))

            display_df = None
            
            if target_product_code:
                # 入力側も念のため6桁に揃える
                search_code = str(target_product_code).strip().zfill(6)
                
                col_c_name = df_req.columns[2] # C列（品番）
                
                # G列（製品コード）から一致する行を探し、C列（品番）を取得
                matched_materials = df_req[df_req[col_g_name] == search_code][col_c_name].unique()
                
                if len(matched_materials) > 0:
                    df_result = create_pivot(df_req, df_inv, df_ord)
                    display_df = df_result[df_result['品番'].isin(matched_materials)]
                else:
                    st.warning(f"製品コード「{search_code}」が見つかりません。")
            else:
                display_df = create_pivot(df_req, df_inv, df_ord)

            # 表示処理（変更なし）
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            if display_df is not None and not display_df.empty:
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
            elif target_product_code:
                st.info("該当する原料の推移データがありません。")
            
        except Exception as e:
            st.error(f"解析エラーが発生しました: {e}")
    else:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #d1d1d1;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
