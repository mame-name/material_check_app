import streamlit as st
import pandas as pd
from calc import create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")

# --- 除外設定リスト ---
EXCLUDE_PART_NUMBERS = ["1999999"]
EXCLUDE_KEYWORDS = ["半製品"]

# --- UIデザイン ---
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

    div.stButton > button {
        width: 100%;
        height: 45px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 3])

if 'filter_mode' not in st.session_state:
    st.session_state.filter_mode = 'normal'

with col1:
    st.markdown("##### 🔍 絞り込み設定")
    
    selected_product_name = "全表示"
    if st.session_state.get('req'):
        try:
            df_req_raw = pd.read_excel(st.session_state.req, header=3)
            df_req_raw.columns = df_req_raw.columns.str.strip()
            col_h_name = df_req_raw.columns[7]
            product_list = sorted(df_req_raw[col_h_name].dropna().unique().tolist())
            selected_product_name = st.selectbox("製品名選択", options=["全表示"] + product_list, label_visibility="collapsed")
        except:
            st.selectbox("製品名選択", options=["全表示"], disabled=True, label_visibility="collapsed")
    else:
        st.selectbox("製品名選択", options=["全表示"], disabled=True, label_visibility="collapsed")

    if st.button("🚨 不足原料のみを表示", use_container_width=True):
        st.session_state.filter_mode = 'shortage'

    if st.button("🔄 全表示に戻す（リセット）", use_container_width=True):
        st.session_state.filter_mode = 'normal'
        st.rerun()

    st.divider()
    st.markdown("##### 📁 データ読込")
    file_req = st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 在庫一覧表", type=['xlsx', 'xls'], key="inv")
    file_ord = st.file_uploader("3. 発注リスト", type=['xlsx', 'xls'], key="ord")

with col2:
    st.markdown("<h1 style='text-align: center;'>原料在庫シミュレーション</h1>", unsafe_allow_html=True)
    st.markdown("---")

    if file_req and file_inv and file_ord:
        try:
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            df_ord = pd.read_excel(file_ord, header=4)
            df_req.columns = df_req.columns.str.strip()
            
            # 1. 全データ計算
            df_raw_result = create_pivot(df_req, df_inv, df_ord)
            
            # 2. ★除外フィルタの適用（3行1セットで削除）
            # 品名が書かれているのはセットの1行目のみ
            exclude_mask = (
                df_raw_result['品番'].isin(EXCLUDE_PART_NUMBERS) | 
                df_raw_result['品名'].str.contains('|'.join(EXCLUDE_KEYWORDS), na=False)
            )
            # 除外対象の開始インデックスを取得
            exclude_start_indices = df_raw_result[exclude_mask].index
            all_exclude_indices = []
            for idx in exclude_start_indices:
                all_exclude_indices.extend([idx, idx+1, idx+2]) # 3行分をリストに追加
            
            # 除外実行とインデックスの振り直し
            df_filtered = df_raw_result.drop(index=all_exclude_indices, errors='ignore').reset_index(drop=True)
            display_df = df_filtered.copy()

            # 3. フィルタリング
            # A. 製品名絞り込み
            if selected_product_name != "全表示":
                col_h_name = df_req.columns[7]
                col_c_name = df_req.columns[2]
                matched_materials = df_req[df_req[col_h_name] == selected_product_name][col_c_name].unique().tolist()
                
                matched_indices = display_df[display_df['品番'].isin(matched_materials)].index
                all_indices = []
                for idx in matched_indices:
                    for offset in [0, 1, 2]:
                        if idx + offset in display_df.index:
                            all_indices.append(idx + offset)
                display_df = display_df.loc[sorted(list(set(all_indices)))]

            # B. 不足原料のみ
            if st.session_state.filter_mode == 'shortage':
                stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
                date_cols = display_df.columns[4:]
                shortage_mask = (stock_rows[date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                
                all_shortage_indices = []
                for idx in shortage_indices:
                    for offset in [-2, -1, 0]:
                        if idx + offset in display_df.index:
                            all_shortage_indices.append(idx + offset)
                display_df = display_df.loc[sorted(list(set(all_shortage_indices)))]

            # 4. 表示
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            if not display_df.empty:
                st.dataframe(
                    display_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
                    use_container_width=True, height=1000, hide_index=True,
                    column_config={
                        "品番": st.column_config.TextColumn("品番", pinned=True),
                        "品名": st.column_config.TextColumn("品名", pinned=True),
                    }
                )
            else:
                st.info("表示可能な原料がありません。")
            
        except Exception as e:
            st.error(f"解析エラーが発生しました: {e}")
    else:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #d1d1d1;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
