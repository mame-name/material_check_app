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

    /* プルダウン、日付入力の枠線デザイン（青枠） */
    div[data-baseweb="select"], 
    div[data-baseweb="date-input-container"],
    div[data-testid="stDateInput"] > div {
        border: 2px solid #1f77b4 !important;
        border-radius: 5px !important;
        background-color: white !important;
        margin-bottom: 20px;
    }

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
        except: pass

    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")

    st.markdown("**表示終了日を指定**")
    default_end = (datetime.now() + timedelta(days=14)).date()
    end_date = st.date_input("終了日", value=default_end, label_visibility="collapsed")
    end_date_str = end_date.strftime('%y/%m/%d')

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
        # データの読み込み
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        # 1. 計算実行
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        if df_raw_result.empty:
            st.warning("計算結果が空です。")
            st.stop()

        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})
        
        # 列の絞り込み
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
        df_limited = df_raw_result[fixed_cols + target_date_cols].copy()

        # 2. 除外フィルタ（品番・品名）
        exclude_mask = (
            df_limited['品番'].isin(EXCLUDE_PART_NUMBERS) | 
            df_limited['品名'].str.contains('|'.join(EXCLUDE_KEYWORDS), na=False)
        )
        df_filtered = df_limited.drop(index=df_limited[exclude_mask].index).reset_index(drop=True)
        
        # 3. フィルタ：製品名
        display_df = df_filtered.copy()
        if st.session_state.selected_product != "全表示":
            col_c_name = df_req.columns[2]
            matched_materials = df_req[df_req[df_req.columns[7]] == st.session_state.selected_product][col_c_name].unique().tolist()
            matched_indices = display_df[display_df['品番'].isin(matched_materials)].index
            all_indices = []
            for idx in matched_indices: all_indices.extend([idx, idx+1, idx+2])
            display_df = display_df.loc[sorted(list(set(all_indices)))]

        # 4. フィルタ：不足原料のみ
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            if target_date_cols:
                shortage_mask = (stock_rows[target_date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                all_short_idx = []
                for idx in shortage_indices: all_short_idx.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[sorted(list(set(all_short_idx)))]

        # 前日在庫の空白化（表示用）
        plot_df = display_df.copy()
        plot_df['前日在庫'] = plot_df['前日在庫'].astype(object)
        plot_df.loc[plot_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        # スタイル設定
        def color_negative_red(val):
            return 'color: red; font-weight: bold;' if isinstance(val, (int, float)) and val < 0 else None

        # --- 表の表示（選択イベント取得） ---
        event = st.dataframe(
            plot_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
            use_container_width=True, 
            height=400, # 内訳表示のために少し高さを調整
            hide_index=True,
            on_select="rerun", # 選択時に情報を取得
            selection_mode="single_row",
            column_config={
                "品番": st.column_config.TextColumn("品番", pinned=True),
                "品名": st.column_config.TextColumn("品名", pinned=True),
            }
        )

        # --- 詳細内訳の表示エリア ---
        st.divider()
        if event and len(event.selection.rows) > 0:
            selected_row_idx = event.selection.rows[0]
            selected_row = plot_df.iloc[selected_row_idx]
            
            # 品番を取得（空文字の場合は上の行を辿る）
            p_code = selected_row['品番']
            p_name = selected_row['品名']
            
            # 納品数や在庫残の行が選ばれた場合、直近の品番を探す
            if not p_code:
                # 選択行から上に辿って品番を探す
                current_idx = selected_row_idx
                while current_idx >= 0 and not plot_df.iloc[current_idx]['品番']:
                    current_idx -= 1
                p_code = plot_df.iloc[current_idx]['品番']
                p_name = plot_df.iloc[current_idx]['品名']

            st.markdown(f"#### 📋 要求内訳: {p_name} ({p_code})")
            
            # df_req（所要量一覧）から詳細を抽出
            # 列インデックス: 2=品番, 7=製品名, 1=要求日, 10=基準単位数量 (データ構造に合わせて調整)
            col_hinban = df_req.columns[2]
            col_seihin = df_req.columns[7]
            col_date = df_req.columns[1]
            col_qty = df_req.columns[10]

            detail_df = df_req[df_req[col_hinban] == p_code][[col_date, col_seihin, col_qty]].copy()
            detail_df.columns = ['要求日', '使用製品名', '要求量']
            
            # 日付順に並び替え
            detail_df['要求日'] = pd.to_datetime(detail_df['要求日'], errors='coerce')
            detail_df = detail_df.sort_values('要求日').dropna(subset=['要求日'])
            detail_df['要求日'] = detail_df['要求日'].dt.strftime('%y/%m/%d')

            # フィルタ：終了日までの分だけ表示
            detail_df = detail_df[detail_df['要求日'] <= end_date_str]

            if not detail_df.empty:
                st.dataframe(detail_df, use_container_width=True, hide_index=True)
            else:
                st.info("この品番の指定期間内の要求詳細はありません。")
        else:
            st.info("👆 表の行をクリックすると、ここに要求の内訳が表示されます。")

    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1;'>データを読み込んでください</p>", unsafe_allow_html=True)
