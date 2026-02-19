import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

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
    div[data-baseweb="select"], div[data-baseweb="date-input-container"] {
        border: 2px solid #1f77b4 !important;
        border-radius: 5px !important;
        background-color: white !important;
        margin-bottom: 20px;
    }
    div[data-baseweb="date-input-container"] input { padding: 8px !important; }
    [data-testid="stWidgetLabel"] p { font-weight: bold; color: #31333F; }
    .stFileUploader { border: 1px solid #e6e9ef; border-radius: 10px; padding: 5px; }
    </style>
    """, unsafe_allow_html=True)

# セッション状態の初期化
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- 1. 左画面（サイドバー）：操作パネル ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み設定")
    
    product_options = ["全表示"]
    if st.session_state.get('req'):
        try:
            df_req_raw = pd.read_excel(st.session_state.req, header=3)
            df_req_raw.columns = df_req_raw.columns.str.strip()
            col_h_name = df_req_raw.columns[7]
            product_options += sorted(df_req_raw[col_h_name].dropna().unique().tolist())
        except:
            pass

    # 1. 製品名プルダウン
    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")

    # 2. 表示終了日（デフォルトは今日+14日）
    st.markdown("**表示終了日を指定**")
    default_date = (datetime.now() + timedelta(days=14)).date()
    end_date = st.date_input("終了日", value=default_date, label_visibility="collapsed")
    
    # 3. 不足トグル
    show_shortage_only = st.toggle("🚨 不足原料のみを表示", value=False)

    st.divider()
    st.markdown("### 📁 データ読込")
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- 2. 右画面（メインエリア）：結果表示 ---
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        # データ読み込みと計算
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        df_raw = create_pivot(df_req, df_inv, df_ord)
        if '現在庫' in df_raw.columns:
            df_raw = df_raw.rename(columns={'現在庫': '前日在庫'})
        
        # --- シンプルな列フィルタリングロジック ---
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        # 文字列に変換した終了日（比較用）
        search_date_str = end_date.strftime('%Y/%m/%d')
        
        # 全列名から、日付に相当する列だけを抽出
        all_date_cols = [c for c in df_raw.columns if c not in fixed_cols]
        
        # カレンダーで選んだ日付「まで」の列を探して、それ以降を捨てる
        final_date_cols = []
        for col in all_date_cols:
            final_date_cols.append(col)
            # もし列名が選択した日付（またはそれ以降の日付）になったら止める
            if pd.to_datetime(col).date() >= end_date:
                break
        
        # 必要な列だけで表を再構成
        display_df = df_raw[fixed_cols + final_date_cols].copy()
        
        # --- 以降、表示用の加工 ---
        # 1. 製品名フィルタ
        if st.session_state.selected_product != "全表示":
            col_h_name = df_req.columns[7]
            col_c_name = df_req.columns[2]
            matched_materials = df_req[df_req[col_h_name] == st.session_state.selected_product][col_c_name].unique().tolist()
            display_df = display_df[display_df['品番'].isin(matched_materials)]

        # 2. 不足フィルタ
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            shortage_indices = stock_rows[(stock_rows[final_date_cols] < 0).any(axis=1)].index
            # 品番ごとに3行セットで表示するため
            all_indices = []
            for idx in shortage_indices:
                all_indices.extend([idx-2, idx-1, idx])
            display_df = display_df.loc[sorted(list(set(all_indices)))]

        # 3. 前日在庫の空白化
        display_df['前日在庫'] = display_df['前日在庫'].astype(object)
        display_df.loc[display_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        # 表の描画
        def color_negative_red(val):
            return 'color: red; font-weight: bold;' if isinstance(val, (int, float)) and val < 0 else None

        st.dataframe(
            display_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
            use_container_width=True, height=800, hide_index=True,
            column_config={"品番": st.column_config.TextColumn(pinned=True), "品名": st.column_config.TextColumn(pinned=True)}
        )
            
    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1;'>データをアップロードしてください</p>", unsafe_allow_html=True)
