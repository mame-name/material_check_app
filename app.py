import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime

# ページ設定
st.set_page_config(layout="wide", page_title="生産管理システム")

# --- UIデザイン（CSS） ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e9ecef;
    }
    header {visibility: hidden;}
    /* 入力欄の青枠デザイン */
    div[data-baseweb="select"], div[data-baseweb="input"] {
        border: 2px solid #1f77b4 !important;
        border-radius: 5px !important;
        background-color: white !important;
        margin-bottom: 20px;
    }
    [data-testid="stWidgetLabel"] p { font-weight: bold; color: #31333F; }
    .stFileUploader { border: 1px solid #e6e9ef; border-radius: 10px; padding: 5px; }
    </style>
    """, unsafe_allow_html=True)

if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- 1. 左画面：操作パネル ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み設定")
    
    # 1. 製品名
    product_options = ["全表示"]
    if st.session_state.get('req'):
        try:
            df_req_raw = pd.read_excel(st.session_state.req, header=3)
            df_req_raw.columns = df_req_raw.columns.str.strip()
            product_options += sorted(df_req_raw[df_req_raw.columns[7]].dropna().unique().tolist())
        except: pass
    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")

    # 2. 表示終了日（直接入力欄）
    st.markdown("**表示終了日を入力**")
    # 初期値として今日の2週間後の日付をセット
    default_date_str = (datetime.now() + pd.Timedelta(days=14)).strftime('%Y/%m/%d')
    end_date_input = st.text_input("終了日入力", value=default_date_str, help="YYYY/MM/DDの形式で入力してください", label_visibility="collapsed")
    
    show_shortage_only = st.toggle("🚨 不足原料のみを表示", value=False)

    st.divider()
    st.markdown("### 📁 データ読込")
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- 2. 右画面：メインエリア ---
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        # 1. 計算実行
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})

        # --- 【直接入力比較ロジック】 ---
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        
        # 入力された文字列を日付オブジェクトに変換（比較用）
        try:
            limit_date = pd.to_datetime(end_date_input)
        except:
            st.error("日付の形式が正しくありません (YYYY/MM/DD)")
            limit_date = pd.to_datetime('2099/12/31') # エラー時は全表示

        cols_to_keep = []
        for col in df_raw_result.columns:
            if col in fixed_cols:
                cols_to_keep.append(col)
                continue
            
            try:
                # 列名も日付として読み込み
                col_date = pd.to_datetime(col)
                # 入力された日付以前のものだけ残す
                if col_date <= limit_date:
                    cols_to_keep.append(col)
            except:
                # 日付として読めない列は捨てる
                continue
        
        display_df = df_raw_result[cols_to_keep].copy()

        # 2. フィルタ：製品名
        if st.session_state.selected_product != "全表示":
            col_c_name = df_req.columns[2]
            materials = df_req[df_req[df_req.columns[7]] == st.session_state.selected_product][col_c_name].unique().tolist()
            matched_indices = display_df[display_df['品番'].isin(materials)].index
            all_idx = []
            for idx in matched_indices: all_idx.extend([idx, idx+1, idx+2])
            display_df = display_df.loc[sorted(list(set(all_idx)))]

        # 3. フィルタ：不足原料
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            date_cols = [c for c in display_df.columns if c not in fixed_cols]
            if date_cols:
                shortage_mask = (stock_rows[date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                all_short_idx = []
                for idx in shortage_indices: all_short_idx.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[sorted(list(set(all_short_idx)))]

        # スタイル設定
        display_df['前日在庫'] = display_df['前日在庫'].astype(object)
        display_df.loc[display_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        def color_red(val):
            return 'color: red; font-weight: bold;' if isinstance(val, (int, float)) and val < 0 else None

        st.dataframe(
            display_df.style.applymap(color_red).format(precision=3, na_rep="0.000"),
            use_container_width=True, height=800, hide_index=True,
            column_config={"品番": st.column_config.TextColumn(pinned=True), "品名": st.column_config.TextColumn(pinned=True)}
        )
            
    except Exception as e:
        st.error(f"エラー: {e}")
else:
    st.info("ファイルをアップロードしてください。")
