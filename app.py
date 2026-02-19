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
    /* 青枠のデザイン */
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
    
    # 1. 製品名プルダウン
    product_options = ["全表示"]
    if st.session_state.get('req'):
        try:
            df_req_temp = pd.read_excel(st.session_state.req, header=3)
            df_req_temp.columns = df_req_temp.columns.str.strip()
            col_h_name = df_req_temp.columns[7]
            product_options += sorted(df_req_temp[col_h_name].dropna().unique().tolist())
        except: pass
    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")

    # 2. 表示終了日（初期値は今日から2週間後）
    st.markdown("**表示終了日を指定**")
    if 'end_date_val' not in st.session_state:
        st.session_state.end_date_val = (datetime.now() + timedelta(days=14)).date()
    end_date = st.date_input("終了日", value=st.session_state.end_date_val, label_visibility="collapsed")
    
    # 3. 不足トグル
    show_shortage_only = st.toggle("🚨 不足原料のみを表示", value=False)

    st.divider()
    st.markdown("### 📁 データ読込")
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- 2. 右画面（メインエリア） ---
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        # A. 基本データの読み込みと計算
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        # 1. 計算実行
        df_raw = create_pivot(df_req, df_inv, df_ord)
        if '現在庫' in df_raw.columns:
            df_raw = df_raw.rename(columns={'現在庫': '前日在庫'})

        # B. 日付による「列」の切り落とし（最優先）
        # 固定列を除いた「日付列」だけをリストアップ
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        all_cols = df_raw.columns.tolist()
        
        # 表示すべき日付列だけを判定して選別
        target_date_cols = []
        for col in all_cols:
            if col not in fixed_cols:
                try:
                    # 列名(日付)がカレンダーで選んだ日付より後なら、そこで追加を止める
                    if pd.to_datetime(col).date() > end_date:
                        continue
                    target_date_cols.append(col)
                except:
                    continue # 日付として読めない列は無視
        
        # ★ ここで表を物理的に作り直す
        display_df = df_raw[fixed_cols + target_date_cols].copy()

        # C. フィルタリング処理（行の絞り込み）
        # 1. 製品名フィルタ
        if st.session_state.selected_product != "全表示":
            col_h_name = df_req.columns[7]
            col_c_name = df_req.columns[2]
            matched_materials = df_req[df_req[col_h_name] == st.session_state.selected_product][col_c_name].unique().tolist()
            display_df = display_df[display_df['品番'].isin(matched_materials)]

        # 2. 不足フィルタ
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            # 絞り込んだ後の日付列（target_date_cols）の中にマイナスがあるか
            if target_date_cols:
                shortage_indices = stock_rows[(stock_rows[target_date_cols] < 0).any(axis=1)].index
                all_indices = []
                for idx in shortage_indices:
                    all_indices.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[sorted(list(set(all_indices)))]

        # D. 表示用の微調整
        # 前日在庫の空白化
        display_df['前日在庫'] = display_df['前日在庫'].astype(object)
        display_df.loc[display_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        # マイナス赤字表示
        def color_negative_red(val):
            return 'color: red; font-weight: bold;' if isinstance(val, (int, float)) and val < 0 else None

        # 表の表示
        st.dataframe(
            display_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
            use_container_width=True, height=800, hide_index=True,
            column_config={
                "品番": st.column_config.TextColumn(pinned=True),
                "品名": st.column_config.TextColumn(pinned=True),
            }
        )
            
    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1;'>左側から3つのファイルをアップロードしてください</p>", unsafe_allow_html=True)
