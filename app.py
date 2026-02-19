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
            df_req_temp = pd.read_excel(st.session_state.req, header=3)
            df_req_temp.columns = df_req_temp.columns.str.strip()
            product_options += sorted(df_req_temp[df_req_temp.columns[7]].dropna().unique().tolist())
        except: pass
    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")

    # 2. 表示終了日（ここで指定した日以降をカットする）
    st.markdown("**表示終了日を指定**")
    end_date = st.date_input("終了日", value=(datetime.now() + timedelta(days=14)).date(), label_visibility="collapsed")
    
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
        # A. データの読み込み
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()

        # B. 【ここがポイント】計算前に「所要量一覧」の列を絞り込む
        # 固定列（インデックス 0〜8 あたり）を保持しつつ、日付列をチェック
        keep_cols = []
        for i, col in enumerate(df_req.columns):
            if i < 9: # 品番や品名などの基本情報列はすべて保持
                keep_cols.append(col)
            else:
                try:
                    # 日付列をチェックし、指定日より後の列はリストに入れない
                    if pd.to_datetime(col).date() <= end_date:
                        keep_cols.append(col)
                except:
                    # 日付として読めない列（合計欄など）は必要に応じて追加
                    continue
        
        # 絞り込んだ後のデータで上書き
        df_req = df_req[keep_cols]

        # C. 計算実行（絞り込み済みの df_req を渡す）
        df_raw = create_pivot(df_req, df_inv, df_ord)
        
        if '現在庫' in df_raw.columns:
            df_raw = df_raw.rename(columns={'現在庫': '前日在庫'})

        # D. フィルタ処理
        display_df = df_raw.copy()

        # 製品名フィルタ
        if st.session_state.selected_product != "全表示":
            col_h_name = df_req.columns[7]
            col_c_name = df_req.columns[2]
            materials = df_req[df_req[col_h_name] == st.session_state.selected_product][col_c_name].unique().tolist()
            display_df = display_df[display_df['品番'].isin(materials)]

        # 不足フィルタ
        if show_shortage_only:
            fixed_names = ['品番', '品名', '区分', '前日在庫']
            date_cols = [c for c in display_df.columns if c not in fixed_names]
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            if date_cols:
                shortage_indices = stock_rows[(stock_rows[date_cols] < 0).any(axis=1)].index
                all_indices = []
                for idx in shortage_indices:
                    all_indices.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[sorted(list(set(all_indices)))]

        # 表示用加工
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
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><p style='text-align: center; color: #d1d1d1;'>データをアップロードしてください</p>", unsafe_allow_html=True)
