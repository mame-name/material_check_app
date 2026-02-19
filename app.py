import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# --- ページ設定 ---
st.set_page_config(layout="wide", page_title="原料在庫量シミュレーション")

# --- 除外設定リスト ---
EXCLUDE_PART_NUMBERS = [1999999]
EXCLUDE_KEYWORDS = ["半製品"]

# --- UIデザイン（横並びラベル・内訳パネル用CSSを完全維持） ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e9ecef;
    }
    header {visibility: hidden;}

    /* 青枠デザイン */
    div[data-baseweb="select"], 
    div[data-baseweb="date-input-container"],
    div[data-testid="stDateInput"] > div {
        border: 2px solid #1f77b4 !important;
        border-radius: 5px !important;
        background-color: white !important;
    }

    /* 横並び用カスタムラベル（右寄せ） */
    .custom-label {
        font-size: 0.9rem;
        font-weight: bold;
        margin-top: 8px;
        white-space: nowrap;
        text-align: right;
        width: 100%;
    }

    /* サイドバー内訳パネル */
    .sidebar-detail-box {
        border-left: 4px solid #1f77b4;
        padding: 0px 10px;
        margin: 10px 0px 20px 0px;
    }
    .detail-title { font-size: 0.85rem; font-weight: bold; color: #1f77b4; margin-bottom: 5px; }

    /* トグルスイッチのラベル太字 */
    [data-testid="stWidgetLabel"] p { font-weight: bold; color: #31333F; }

    /* アップローダーのデザイン */
    .stFileUploader { border: 1px solid #e6e9ef; border-radius: 10px; padding: 5px; }
    [data-testid="stFileUploaderSmallNumber"] { display: none !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploader"] section { padding: 0px 10px !important; min-height: 50px !important; }
    </style>
    """, unsafe_allow_html=True)

if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- メイン処理 ---
# 4つのファイルが揃っているか確認
if all(st.session_state.get(k) for k in ['req', 'inv', 'ord', 'ord_sched']):
    try:
        # Excel読み込み
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_ord_sched = pd.read_excel(st.session_state.ord_sched, header=2)
        df_req.columns = df_req.columns.str.strip()
        
        # 1. 計算実行（発注予定を追加）
        df_raw_result = create_pivot(df_req, df_inv, df_ord, df_ord_sched)
        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})

        # --- サイドバー操作パネル ---
        with st.sidebar:
            st.markdown("### 🔍 絞り込み設定")
            
            # 比率 [0.7, 2.5] を維持
            col_lab1, col_inp1 = st.columns([0.7, 2.5])
            with col_lab1:
                st.markdown('<p class="custom-label">品名：</p>', unsafe_allow_html=True)
            with col_inp1:
                col_h_name = df_req.columns[7]
                product_options = ["全表示"] + sorted(df_req[col_h_name].dropna().unique().tolist())
                st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")
            
            col_lab2, col_inp2 = st.columns([0.7, 2.5])
            with col_lab2:
                st.markdown('<p class="custom-label">日付：</p>', unsafe_allow_html=True)
            with col_inp2:
                default_end = (datetime.now() + timedelta(days=14)).date()
                end_date = st.date_input("終了日", value=default_end, label_visibility="collapsed")
                end_date_str = end_date.strftime('%y/%m/%d')
            
            col_spacer, col_toggle = st.columns([0.07, 2.5])
            with col_toggle:
                show_shortage_only = st.toggle(" 🚨不足する原料のみ表示", value=False)

            # --- サイドバー内訳エリア ---
            st.markdown("---")
            detail_placeholder = st.empty() 
            st.markdown("---")

            st.markdown("### 📁 データ読込")
            st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
            st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
            st.file_uploader("3. 発注予定一覧", type=['xlsx', 'xls'], key="ord_sched")
            st.file_uploader("4. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

        # --- フィルタロジック ---
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
        df_limited = df_raw_result[fixed_cols + target_date_cols].copy()

        # 2. 除外フィルタ
        exclude_mask = (
            df_limited['品番'].isin(EXCLUDE_PART_NUMBERS) | 
            df_limited['品名'].str.contains('|'.join(EXCLUDE_KEYWORDS), na=False)
        )
        exclude_indices = df_limited[exclude_mask].index
        all_exclude = []
        for idx in exclude_indices:
            all_exclude.extend([idx, idx+1, idx+2])
        df_filtered = df_limited.drop(index=all_exclude, errors='ignore').reset_index(drop=True)
        
        display_df = df_filtered.copy()
        display_df['前日在庫'] = display_df['前日在庫'].astype(object)
        display_df.loc[display_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        # 3. 製品名フィルタ
        if st.session_state.selected_product != "全表示":
            col_c_name = df_req.columns[2]
            matched_materials = df_req[df_req[df_req.columns[7]] == st.session_state.selected_product][col_c_name].unique().tolist()
            matched_indices = display_df[display_df['品番'].isin(matched_materials)].index
            all_indices = []
            for idx in matched_indices:
                all_indices.extend([idx, idx+1, idx+2])
            display_df = display_df.loc[sorted(list(set(all_indices)))]

        # 4. 不足原料フィルタ
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            if target_date_cols:
                shortage_mask = (stock_rows[target_date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                all_short_idx = []
                for idx in shortage_indices:
                    all_short_idx.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[sorted(list(set(all_short_idx)))]

        # --- スタイル関数（3行ごとに色付け） ---
        def style_row_groups(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            for i in range(len(df)):
                group_no = i // 3
                if group_no % 2 == 1:
                    styles.iloc[i, :] = 'background-color: #f2f7fb'
            return styles

        # 数値フォーマット（0を空白、品番には小数点なし）
        def format_values(val):
            if isinstance(val, (int, float)):
                if val == 0: return ""
                return f"{val:.3f}"
            return val

        num_cols = [c for c in display_df.columns if c not in ['品番', '品名', '区分']]

        # メインテーブル表示
        st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)
        
        event = st.dataframe(
            display_df.style.apply(style_row_groups, axis=None)
            .applymap(lambda v: 'color:red;font-weight:bold;' if isinstance(v,(int,float)) and v<0 else None)
            .format(format_values, subset=num_cols, na_rep=""),
            use_container_width=True, 
            height=600, 
            hide_index=True,
            on_select="rerun", 
            selection_mode="single-cell",
            column_config={
                "品番": st.column_config.TextColumn("品番", pinned=True, width=60, color="#333333"),
                "品名": st.column_config.TextColumn("品名", pinned=True, width=200, color="#333333"),
            }
        )

        # --- 内訳表示ロジック（完全に維持） ---
        if event and len(event.selection.cells) > 0:
            cell = event.selection.cells[0]
            r_val = cell.get('row') if isinstance(cell, dict) else cell[0]
            c_val = cell.get('column') if isinstance(cell, dict) else cell[1]
            r_idx = int(r_val[0] if isinstance(r_val, list) else r_val)
            
            if isinstance(c_val, str): 
                sel_date = c_val
            else: 
                sel_date = display_df.columns[int(c_val[0] if isinstance(c_val, list) else c_val)]

            row_data = display_df.iloc[r_idx]

            if row_data['区分'] == '要求量 (ー)' and sel_date not in fixed_cols:
                target_code = str(row_data['品番']).strip()
                target_name = row_data['品名']
                
                d_hinban = df_req.iloc[:, 2].astype(str).str.strip()
                detail_df = df_req[d_hinban == target_code].copy()
                detail_df['date_match'] = pd.to_datetime(detail_df.iloc[:, 5], errors='coerce').dt.strftime('%y/%m/%d')
                res = detail_df[detail_df['date_match'] == sel_date].copy()

                with detail_placeholder.container():
                    st.markdown(f'<div class="sidebar-detail-box"><div class="detail-title">📍 {sel_date} {target_name}</div></div>', unsafe_allow_html=True)
                    if not res.empty:
                        v_df = res.iloc[:, [7, 11]].copy()
                        v_df.columns = ['使用製品', '数量']
                        v_df = v_df.groupby(['使用製品'])['数量'].sum().reset_index()
                        st.dataframe(v_df, hide_index=True, use_container_width=True)
                    else:
                        st.caption("明細なし")

    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    with st.sidebar:
        st.markdown("### 📁 データ読込")
        st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
        st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
        st.file_uploader("3. 発注予定一覧", type=['xlsx', 'xls'], key="ord_sched")
        st.file_uploader("4. 在庫一覧表", type=['xlsx', 'xls'], key="inv")
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1; font-size: 1.2rem;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
