import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# --- 1. ページ設定 & デザイン ---
st.set_page_config(layout="wide", page_title="生産管理システム")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    /* プルダウン、日付入力の枠線デザイン（青枠） */
    div[data-baseweb="select"], 
    div[data-baseweb="date-input-container"],
    div[data-testid="stDateInput"] > div {
        border: 2px solid #1f77b4 !important;
        border-radius: 5px !important;
        background-color: white !important;
        margin-bottom: 20px;
    }

    /* トグルスイッチのラベルを太字にする */
    [data-testid="stWidgetLabel"] p {
        font-weight: bold;
        color: #31333F;
    }

    /* アップローダーのデザイン */
    .stFileUploader { border: 1px solid #e6e9ef; border-radius: 10px; padding: 5px; }
    [data-testid="stFileUploaderSmallNumber"] { display: none !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploader"] section { padding: 0px 10px !important; min-height: 50px !important; }
    </style>
    """, unsafe_allow_html=True)

# セッション状態の初期化
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- 2. 左画面（サイドバー）：操作パネル ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み設定")
    
    # 製品名リストの作成
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

    # 2. 表示終了日指定（青枠付き）
    st.markdown("**表示終了日を指定**")
    default_end = (datetime.now() + timedelta(days=14)).date()
    end_date = st.date_input("終了日", value=default_end, label_visibility="collapsed")
    
    # calc.pyの「年2桁文字列」に合わせて変換（ここが絞り込みの肝）
    end_date_str = end_date.strftime('%y/%m/%d')

    # 3. トグルスイッチ
    show_shortage_only = st.toggle("🚨 不足原料のみを表示", value=False)

    st.divider()
    st.markdown("### 📁 データ読込")
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- 3. 右画面（メインエリア）：結果表示 ---
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        # データ読込
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        # A. 計算実行
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        
        if df_raw_result.empty:
            st.warning("計算結果が空です。")
            st.stop()

        # 列名変更
        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})
        
        # B. 【日付による列の絞り込み】
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        # calc.pyが生成した列名（%y/%m/%d形式の文字列）とカレンダー入力を比較
        target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
        
        # 物理的に列を抽出
        df_limited = df_raw_result[fixed_cols + target_date_cols].copy()

        # C. フィルタリング（製品名選択）
        display_df = df_limited.copy()
        if st.session_state.selected_product != "全表示":
            col_c_name = df_req.columns[2]
            matched_materials = df_req[df_req[df_req.columns[7]] == st.session_state.selected_product][col_c_name].unique().tolist()
            matched_indices = display_df[display_df['品番'].isin(matched_materials)].index
            all_indices = []
            for idx in matched_indices:
                all_indices.extend([idx, idx+1, idx+2])
            display_df = display_df.loc[sorted(list(set(all_indices)))]

        # D. フィルタリング（不足のみ）
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            if target_date_cols:
                shortage_mask = (stock_rows[target_date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                all_short_idx = []
                for idx in shortage_indices:
                    all_short_idx.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[sorted(list(set(all_short_idx)))]

        # 表示用加工（在庫残以外の前日在庫を消す）
        display_df['前日在庫'] = display_df['前日在庫'].astype(object)
        display_df.loc[display_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        # スタイル（マイナスを赤字に）
        def color_negative_red(val):
            if isinstance(val, (int, float)) and val < 0:
                return 'color: red; font-weight: bold;'
            return None

        # データフレーム表示
        st.dataframe(
            display_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
            use_container_width=True, height=800, hide_index=True,
            column_config={
                "品番": st.column_config.TextColumn("品番", pinned=True),
                "品名": st.column_config.TextColumn("品名", pinned=True),
            }
        )
            
    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #d1d1d1; font-size: 1.2rem;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
