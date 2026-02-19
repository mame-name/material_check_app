import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(layout="wide", page_title="生産管理システム")

# --- 除外設定リスト ---
EXCLUDE_PART_NUMBERS = [1999999]
EXCLUDE_KEYWORDS = ["半製品"]

# --- UIデザイン（CSS） ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e9ecef;
    }
    header {visibility: hidden;}

    /* プルダウンと日付入力の枠線デザイン（青枠） */
    div[data-baseweb="select"], div[data-baseweb="date-input-container"] {
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

# --- 1. 左画面（サイドバー）：操作パネル ---
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

    # 1. 製品名プルダウン（青枠付き）
    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")

    # 2. 日付範囲設定（青枠付き）
    st.markdown("**表示終了日を指定**")
    # 初期値：今日 + 14日
    default_end = (datetime.now() + timedelta(days=14)).date()
    end_date = st.date_input("終了日", value=default_end, label_visibility="collapsed")

    # 3. トグルスイッチ
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
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        # 1. 計算実行
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        
        # 列名変更：現在庫 → 前日在庫
        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})
        
        # --- 【強化版】列の絞り込みロジック ---
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        
        def is_target_column(col_name):
            # 固定列は必ず残す
            if col_name in fixed_cols:
                return True
            try:
                # 列名を日付に変換して比較（型エラーを防ぐため慎重に変換）
                col_dt = pd.to_datetime(col_name).date()
                return col_dt <= end_date
            except:
                # 日付として解釈できないイレギュラーな列は落とす
                return False

        # 全列名を検査
        target_cols = [c for c in df_raw_result.columns if is_target_column(c)]
        # 物理的に列を制限したデータフレームを作成
        df_limited = df_raw_result[target_cols].copy()

        # 2. 除外フィルタ（品番・品名キーワード）
        exclude_mask = (
            df_limited['品番'].astype(str).isin([str(x) for x in EXCLUDE_PART_NUMBERS]) | 
            df_limited['品名'].astype(str).str.contains('|'.join(EXCLUDE_KEYWORDS), na=False)
        )
        exclude_start_indices = df_limited[exclude_mask].index
        all_exclude_indices = []
        for idx in exclude_start_indices:
            all_exclude_indices.extend([idx, idx+1, idx+2])
        
        df_filtered = df_limited.drop(index=all_exclude_indices, errors='ignore').reset_index(drop=True)
        
        # --- 表示用の加工（空白化処理） ---
        display_df = df_filtered.copy()
        display_df['前日在庫'] = display_df['前日在庫'].astype(object)
        display_df.loc[display_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        # 3. フィルタ：製品名
        if st.session_state.selected_product != "全表示":
            col_h_name = df_req.columns[7]
            col_c_name = df_req.columns[2]
            matched_materials = df_req[df_req[col_h_name] == st.session_state.selected_product][col_c_name].unique().tolist()
            # 品番を文字列比較で確実にマッチング
            matched_materials = [str(m) for m in matched_materials]
            matched_indices = display_df[display_df['品番'].astype(str).isin(matched_materials)].index
            all_indices = []
            for idx in matched_indices:
                for offset in [0, 1, 2]:
                    if idx + offset in display_df.index:
                        all_indices.append(idx + offset)
            display_df = display_df.loc[sorted(list(set(all_indices)))]

        # 4. フィルタ：不足原料のみ（現在表示されている列だけで判定）
        active_date_cols = [c for c in display_df.columns if c not in fixed_cols]
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            if active_date_cols:
                shortage_mask = (stock_rows[active_date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                all_shortage_indices = []
                for idx in shortage_indices:
                    for offset in [-2, -1, 0]:
                        if idx + offset in display_df.index:
                            all_shortage_indices.append(idx + offset)
                display_df = display_df.loc[sorted(list(set(all_shortage_indices)))]

        # マイナス値を赤字にする
        def color_negative_red(val):
            if isinstance(val, (int, float)) and val < 0:
                return 'color: red; font-weight: bold;'
            return None

        if not display_df.empty:
            st.dataframe(
                display_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
                use_container_width=True, height=800, hide_index=True,
                column_config={
                    "品番": st.column_config.TextColumn("品番", pinned=True),
                    "品名": st.column_config.TextColumn("品名", pinned=True),
                }
            )
        else:
            st.info("表示範囲内にデータがないか、フィルタ条件に一致しません。")
            
    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #d1d1d1; font-size: 1.2rem;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
