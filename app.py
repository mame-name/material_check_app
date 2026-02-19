import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(layout="wide", page_title="生産管理システム")

# --- UIデザイン ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e9ecef; }
    header {visibility: hidden;}
    div[data-baseweb="select"], div[data-baseweb="date-input-container"] {
        border: 2px solid #1f77b4 !important; border-radius: 5px !important; margin-bottom: 20px;
    }
    div[data-baseweb="date-input-container"] input { padding: 8px !important; }
    [data-testid="stWidgetLabel"] p { font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# セッション状態
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- 1. サイドバー ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み設定")
    
    # 製品名リスト（ここは既存通り）
    product_options = ["全表示"]
    if st.session_state.get('req'):
        try:
            temp = pd.read_excel(st.session_state.req, header=3)
            temp.columns = temp.columns.str.strip()
            product_options += sorted(temp[temp.columns[7]].dropna().unique().tolist())
        except: pass
    
    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")

    # 表示終了日（初期値は今日+14日）
    st.markdown("**表示終了日を指定**")
    default_end = (datetime.now() + timedelta(days=14)).date()
    end_date = st.date_input("終了日", value=default_end, label_visibility="collapsed")
    
    show_shortage = st.toggle("🚨 不足原料のみを表示", value=False)

    st.divider()
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- 2. メインエリア ---
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        # 計算
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        df_raw = create_pivot(df_req, df_inv, df_ord)
        if '現在庫' in df_raw.columns:
            df_raw = df_raw.rename(columns={'現在庫': '前日在庫'})

        # --- 【超単純ロジック】列の絞り込み ---
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        
        # 1. まず表示したい「日付列」だけを抜き出す
        active_date_cols = []
        for col in df_raw.columns:
            if col not in fixed_cols:
                # 列名を日付に変換して比較（カレンダーのend_date以下なら採用）
                try:
                    if pd.to_datetime(col).date() <= end_date:
                        active_date_cols.append(col)
                except:
                    pass 
        
        # 2. 固定列と、絞った日付列をガッチャンコする
        display_df = df_raw[fixed_cols + active_date_cols].copy()

        # --- フィルタ ---
        if st.session_state.selected_product != "全表示":
            col_c_name = df_req.columns[2]
            materials = df_req[df_req[df_req.columns[7]] == st.session_state.selected_product][col_c_name].unique()
            display_df = display_df[display_df['品番'].isin(materials)]

        if show_shortage:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            # いま表示されている日付列（active_date_cols）だけで不足判定
            shortage_mask = (stock_rows[active_date_cols] < 0).any(axis=1)
            indices = stock_rows[shortage_mask].index
            all_idx = []
            for i in indices: all_idx.extend([i-2, i-1, i])
            display_df = display_df.loc[sorted(list(set(all_idx)))]

        # 前日在庫の調整
        display_df['前日在庫'] = display_df['前日在庫'].astype(object)
        display_df.loc[display_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        # 表示
        def color_red(val):
            return 'color: red; font-weight: bold;' if isinstance(val, (int, float)) and val < 0 else None

        st.dataframe(
            display_df.style.applymap(color_red).format(precision=3, na_rep="0.000"),
            use_container_width=True, height=800, hide_index=True,
            column_config={"品番": st.column_config.TextColumn(pinned=True), "品名": st.column_config.TextColumn(pinned=True)}
        )
            
    except Exception as e:
        st.error(f"エラー内容: {e}")
else:
    st.info("ファイルをアップロードしてください。")
