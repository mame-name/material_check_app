import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# --- 1. ページ設定 & デザイン ---
st.set_page_config(layout="wide", page_title="生産管理システム")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    /* サイドバーの入力項目に青枠を適用 */
    div[data-baseweb="select"], 
    div[data-baseweb="date-input-container"],
    div[data-testid="stDateInput"] > div {
        border: 2px solid #1f77b4 !important;
        border-radius: 5px !important;
        background-color: white !important;
        margin-bottom: 20px;
    }
    /* 詳細エリアのスタイル */
    .detail-container {
        background-color: #f0f8ff;
        border-left: 5px solid #1f77b4;
        padding: 15px;
        border-radius: 5px;
        margin-top: 10px;
    }
    [data-testid="stWidgetLabel"] p { font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# セッション状態の初期化
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- 2. サイドバー：操作パネル ---
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
        except: pass

    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")

    st.markdown("**表示終了日を指定**")
    default_end = (datetime.now() + timedelta(days=14)).date()
    end_date = st.date_input("終了日", value=default_end, label_visibility="collapsed")
    # calc.pyの「年2桁文字列」に合わせる
    end_date_str = end_date.strftime('%y/%m/%d')

    show_shortage_only = st.toggle("🚨 不足原料のみを表示", value=False)

    st.divider()
    st.markdown("### 📁 データ読込")
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- 3. メインエリア ---
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        # データ読み込み
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
        
        # 2. 列の絞り込み（終了日以前の列のみ抽出）
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
        df_limited = df_raw_result[fixed_cols + target_date_cols].copy()

        # 3. フィルタリング（製品名・不足）
        display_df = df_limited.copy()
        if st.session_state.selected_product != "全表示":
            col_c_name = df_req.columns[2]
            matched_materials = df_req[df_req[df_req.columns[7]] == st.session_state.selected_product][col_c_name].unique().tolist()
            matched_indices = display_df[display_df['品番'].isin(matched_materials)].index
            all_indices = []
            for idx in matched_indices: all_indices.extend([idx, idx+1, idx+2])
            display_df = display_df.loc[sorted(list(set(all_indices)))]

        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            if target_date_cols:
                shortage_mask = (stock_rows[target_date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                all_short_idx = []
                for idx in shortage_indices: all_short_idx.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[sorted(list(set(all_short_idx)))]

        # 表示用加工
        plot_df = display_df.copy()
        plot_df['前日在庫'] = plot_df['前日在庫'].astype(object)
        plot_df.loc[plot_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        def color_negative_red(val):
            return 'color: red; font-weight: bold;' if isinstance(val, (int, float)) and val < 0 else None

        # --- メインテーブル表示 (選択イベントを有効化) ---
        st.info("💡 行を選択すると、その下に詳細な要求内訳が表示されます。")
        selection_event = st.dataframe(
            plot_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
            use_container_width=True, 
            height=400, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single_row",
            column_config={
                "品番": st.column_config.TextColumn("品番", pinned=True),
                "品名": st.column_config.TextColumn("品名", pinned=True),
            }
        )

        # --- 4. 詳細表示エリア（動的差し込み） ---
        if selection_event and len(selection_event.selection.rows) > 0:
            selected_idx = selection_event.selection.rows[0]
            selected_row_data = plot_df.iloc[selected_idx]
            
            # 品番特定ロジック（空白行なら上に辿る）
            target_p_code = selected_row_data['品番']
            if not target_p_code:
                current_search_idx = selected_idx
                while current_search_idx >= 0 and not plot_df.iloc[current_search_idx]['品番']:
                    current_search_idx -= 1
                target_p_code = plot_df.iloc[current_search_idx]['品番']
                target_p_name = plot_df.iloc[current_search_idx]['品名']
            else:
                target_p_name = selected_row_data['品名']

            # 内訳データの抽出 (df_reqから)
            col_hinban = df_req.columns[2]
            col_seihin = df_req.columns[7]
            col_date = df_req.columns[1]
            col_qty = df_req.columns[10]

            detail = df_req[df_req[col_hinban] == target_p_code][[col_date, col_seihin, col_qty]].copy()
            detail.columns = ['要求日', '使用製品', '要求量']
            
            # 型変換と並び替え
            detail['要求日'] = pd.to_datetime(detail['要求日'], errors='coerce')
            detail = detail.sort_values('要求日').dropna(subset=['要求日'])
            detail['要求日'] = detail['要求日'].dt.strftime('%y/%m/%d')
            
            # カレンダーの終了日までの分に絞り込む
            detail = detail[detail['要求日'] <= end_date_str]

            # 詳細画面の表示
            st.markdown(f"""
                <div class="detail-container">
                    <h4>📋 内訳詳細: {target_p_name} ({target_p_code})</h4>
                </div>
                """, unsafe_allow_html=True)
            
            if not detail.empty:
                st.dataframe(detail, use_container_width=True, hide_index=True)
            else:
                st.write("指定期間内の詳細データはありません。")
        
    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1;'>ファイルをアップロードしてください</p>", unsafe_allow_html=True)
