import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# --- UIデザイン ---
st.set_page_config(layout="wide", page_title="生産管理システム")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e9ecef; }
    header {visibility: hidden;}
    
    /* 入力エリアの青枠 */
    div[data-baseweb="select"], div[data-baseweb="date-input-container"], div[data-testid="stDateInput"] > div {
        border: 2px solid #1f77b4 !important; border-radius: 5px !important;
        background-color: white !important; margin-bottom: 20px;
    }
    
    /* サイドバー内訳のシンプル枠 */
    .sidebar-detail-box {
        border-left: 4px solid #1f77b4;
        padding: 0px 10px;
        margin: 10px 0px 20px 0px;
    }
    .detail-title { font-size: 0.85rem; font-weight: bold; color: #1f77b4; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- データ計算処理 ---
df_to_plot = None
detail_content = None

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})
        
        # 基本表示データ作成
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        # サイドバーで使うための終了日取得（先に計算が必要なためここでおこなう）
        default_end_str = (datetime.now() + timedelta(days=14)).strftime('%y/%m/%d')
        
        # --- メイン画面描画 ---
        st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)
        
        # フィルタと表示用DFの作成
        # (サイドバーの値を参照するため、後続の st.sidebar 内で最終確定させる)
    except Exception as e:
        st.error(f"解析エラー: {e}")

# --- サイドバー表示 ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み設定")
    
    if st.session_state.get('req'):
        product_options = ["全表示"] + sorted(df_req.iloc[:, 7].dropna().unique().tolist())
    else:
        product_options = ["全表示"]
        
    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")
    end_date = st.date_input("終了日", value=(datetime.now() + timedelta(days=14)).date(), label_visibility="collapsed")
    end_date_str = end_date.strftime('%y/%m/%d')
    show_shortage_only = st.toggle("🚨 不足原料のみを表示", value=False)

    # --- 内訳表示エリア（シンプル版） ---
    st.markdown("---")
    detail_container = st.empty() # ここに内訳を差し込む
    st.markdown("---")

    st.markdown("### 📁 データ読込")
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- メイン画面テーブルのフィルタと表示 ---
if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
    display_df = df_raw_result[fixed_cols + target_date_cols].copy()

    if st.session_state.selected_product != "全表示":
        matched_materials = df_req[df_req.iloc[:, 7] == st.session_state.selected_product].iloc[:, 2].unique().tolist()
        display_df = display_df[display_df['品番'].isin(matched_materials) | (display_df['品番'] == "")]

    if show_shortage_only:
        stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
        if target_date_cols:
            shortage_mask = (stock_rows[target_date_cols] < 0).any(axis=1)
            shortage_indices = stock_rows[shortage_mask].index
            all_short_idx = []
            for idx in shortage_indices: all_short_idx.extend([idx-2, idx-1, idx])
            display_df = display_df.loc[display_df.index.intersection(all_short_idx)]

    plot_df = display_df.copy().reset_index(drop=True)
    plot_df['前日在庫'] = plot_df['前日在庫'].astype(object)
    plot_df.loc[plot_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

    event = st.dataframe(
        plot_df.style.applymap(lambda v: 'color:red;font-weight:bold;' if isinstance(v,(int,float)) and v<0 else None).format(precision=3),
        use_container_width=True, height=600, hide_index=True,
        on_select="rerun", selection_mode="single-cell"
    )

    # --- セル選択時のサイドバー書き換え ---
    if event and len(event.selection.cells) > 0:
        cell = event.selection.cells[0]
        r_idx = int(cell.get('row')[0] if isinstance(cell.get('row'), list) else cell.get('row'))
        c_val = cell.get('column')
        sel_date = c_val if isinstance(c_val, str) else plot_df.columns[int(c_val[0] if isinstance(c_val, list) else c_val)]
        
        row_data = plot_df.iloc[r_idx]

        if row_data['区分'] == '要求量 (ー)' and sel_date not in fixed_cols:
            target_code = str(row_data['品番']).strip()
            d_hinban = df_req.iloc[:, 2].astype(str).str.strip()
            detail_df = df_req[d_hinban == target_code].copy()
            detail_df['date_match'] = pd.to_datetime(detail_df.iloc[:, 5], errors='coerce').dt.strftime('%y/%m/%d')
            res = detail_df[detail_df['date_match'] == sel_date].copy()

            with detail_container:
                st.markdown(f'<div class="sidebar-detail-box"><div class="detail-title">📍 {sel_date} 内訳</div></div>', unsafe_allow_html=True)
                if not res.empty:
                    v_df = res.iloc[:, [7, 11]].copy()
                    v_df.columns = ['使用製品', '数量']
                    v_df = v_df.groupby(['使用製品'])['数量'].sum().reset_index()
                    st.dataframe(v_df, hide_index=True, use_container_width=True)
                else:
                    st.caption("明細なし")
else:
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1;'>データをアップロードしてください</p>", unsafe_allow_html=True)
    
