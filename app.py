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

    /* プルダウン、日付入力、テキスト入力の枠線デザイン（青枠） */
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
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        if df_raw_result.empty:
            st.warning("計算結果が空です。")
            st.stop()

        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})
        
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
        df_limited = df_raw_result[fixed_cols + target_date_cols].copy()

        # 除外フィルタ
        exclude_mask = (df_limited['品番'].isin(EXCLUDE_PART_NUMBERS) | df_limited['品名'].str.contains('|'.join(EXCLUDE_KEYWORDS), na=False))
        df_filtered = df_limited.drop(index=df_limited[exclude_mask].index).reset_index(drop=True)
        
        display_df = df_filtered.copy()
        
        # フィルタ：製品名
        if st.session_state.selected_product != "全表示":
            col_c_name = df_req.columns[2]
            matched_materials = df_req[df_req[df_req.columns[7]] == st.session_state.selected_product][col_c_name].unique().tolist()
            matched_indices = display_df[display_df['品番'].isin(matched_materials)].index
            all_indices = []
            for idx in matched_indices: all_indices.extend([idx, idx+1, idx+2])
            display_df = display_df.loc[sorted(list(set(all_indices)))]

        # フィルタ：不足原料のみ
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            if target_date_cols:
                shortage_mask = (stock_rows[target_date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                all_short_idx = []
                for idx in shortage_indices: all_short_idx.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[sorted(list(set(all_short_idx)))]

        plot_df = display_df.copy()
        plot_df['前日在庫'] = plot_df['前日在庫'].astype(object)
        plot_df.loc[plot_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        def color_negative_red(val):
            return 'color: red; font-weight: bold;' if isinstance(val, (int, float)) and val < 0 else None

        # --- 表の表示 (single-cellモード) ---
        event = st.dataframe(
            plot_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
            use_container_width=True, height=500, hide_index=True,
            on_select="rerun",
            selection_mode="single-cell", # セル選択に変更
            column_config={
                "品番": st.column_config.TextColumn("品番", pinned=True),
                "品名": st.column_config.TextColumn("品名", pinned=True),
            }
        )

        # --- 選択されたセルに基づいた内訳表示 ---
        if event and len(event.selection.cells) > 0:
            cell = event.selection.cells[0]
            row_idx = cell['row']
            col_idx = cell['column']
            
            # 列名（日付）を取得
            selected_col_name = plot_df.columns[col_idx]
            
            # 固定列（品番・品名・区分・前日在庫）が選ばれた場合は無視
            if selected_col_name in fixed_cols:
                st.info("日付のマス（要求量）を選択してください。")
            else:
                # 品番を特定（3行セット対応）
                selected_p_code = plot_df.iloc[row_idx]['品番']
                if not selected_p_code:
                    for i in range(1, 3):
                        if row_idx - i >= 0:
                            code = plot_df.iloc[row_idx - i]['品番']
                            if code:
                                selected_p_code = code
                                selected_p_name = plot_df.iloc[row_idx - i]['品名']
                                break
                else:
                    selected_p_name = plot_df.iloc[row_idx]['品名']

                # 内訳抽出
                col_hinban = df_req.columns[2]
                col_seihin = df_req.columns[7]
                col_date_orig = df_req.columns[1]
                col_qty = df_req.columns[10]

                # 元データの要求日を文字列に変換して比較
                detail = df_req[df_req[col_hinban] == selected_p_code].copy()
                detail['要求日_str'] = pd.to_datetime(detail[col_date_orig]).dt.strftime('%y/%m/%d')
                
                # 特定の「日付」と「品番」で絞り込み
                specific_detail = detail[detail['要求日_str'] == selected_col_name][[col_date_orig, col_seihin, col_qty]]
                specific_detail.columns = ['要求日', '使用製品名', '要求量']

                st.markdown(f"#### 🔍 {selected_col_name} の内訳: {selected_p_name}")
                if not specific_detail.empty:
                    st.table(specific_detail) # その場で見やすいようにコンパクトに
                else:
                    st.write("この日の要求はありません（在庫計算上の0表示など）。")
        else:
            st.info("👆 表の中の「数字（マス）」をクリックすると、その日の要求内訳が表示されます。")
            
    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1;'>データをアップロードしてください</p>", unsafe_allow_html=True)
