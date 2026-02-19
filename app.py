import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# --- ページ設定 & デザイン ---
st.set_page_config(layout="wide", page_title="生産管理システム")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-baseweb="select"], div[data-baseweb="date-input-container"], div[data-testid="stDateInput"] > div {
        border: 2px solid #1f77b4 !important; border-radius: 5px !important;
        background-color: white !important; margin-bottom: 20px;
    }
    .detail-area {
        background-color: #f0f8ff; border: 2px solid #1f77b4;
        border-radius: 10px; padding: 15px; margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- サイドバー ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み設定")
    product_options = ["全表示"]
    if st.session_state.get('req'):
        try:
            df_req_raw = pd.read_excel(st.session_state.req, header=3)
            df_req_raw.columns = df_req_raw.columns.str.strip()
            product_options += sorted(df_req_raw[df_req_raw.columns[7]].dropna().unique().tolist())
        except: pass

    st.selectbox("製品名選択", options=product_options, key="selected_product", label_visibility="collapsed")
    end_date = st.date_input("終了日", value=(datetime.now() + timedelta(days=14)).date(), label_visibility="collapsed")
    end_date_str = end_date.strftime('%y/%m/%d')
    show_shortage_only = st.toggle("🚨 不足原料のみを表示", value=False)

    st.divider()
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- メインエリア ---
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})
        
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
        display_df = df_raw_result[fixed_cols + target_date_cols].copy()

        # フィルタ処理
        if st.session_state.selected_product != "全表示":
            matched_materials = df_req[df_req[df_req.columns[7]] == st.session_state.selected_product][df_req.columns[2]].unique().tolist()
            display_df = display_df[display_df['品番'].isin(matched_materials) | (display_df['品番'] == "")]

        plot_df = display_df.copy().reset_index(drop=True)
        plot_df['前日在庫'] = plot_df['前日在庫'].astype(object)
        plot_df.loc[plot_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        st.info("💡 「要求量」の行の数字（セル）をクリックすると、その日の内訳を表示します")
        
        # --- セル選択の設定 ---
        event = st.dataframe(
            plot_df.style.applymap(lambda v: 'color:red;font-weight:bold;' if isinstance(v,(int,float)) and v<0 else None).format(precision=3),
            use_container_width=True, height=500, hide_index=True,
            on_select="rerun", selection_mode="single-cell"
        )

        # --- 最終解：列名ダイレクト取得ロジック ---
        if event and len(event.selection.cells) > 0:
            cell_info = event.selection.cells[0]
            
            # 1. 行の特定（辞書でもタプルでも対応）
            r_val = cell_info.get('row') if isinstance(cell_info, dict) else cell_info[0]
            r_idx = int(r_val[0] if isinstance(r_val, list) else r_val)
            
            # 2. 列の特定（ここが修正のキモ）
            # columnに直接 '26/02/20' のような文字列が入ってくるケースに対応
            c_val = cell_info.get('column') if isinstance(cell_info, dict) else cell_info[1]
            if isinstance(c_val, str):
                selected_date = c_val  # 文字列ならそのまま日付として使う
            else:
                c_idx = int(c_val[0] if isinstance(c_val, list) else c_val)
                selected_date = plot_df.columns[c_idx]

            # 3. データの取得
            row_data = plot_df.iloc[r_idx]

            if row_data['区分'] == '要求量 (ー)' and selected_date not in fixed_cols:
                target_code = row_data['品番']
                target_name = row_data['品名']
                
                if target_code:
                    col_hinban = df_req.columns[2]
                    col_date = df_req.columns[1]
                    col_seihin = df_req.columns[7]
                    col_qty = df_req.columns[10]

                    detail_df = df_req[df_req[col_hinban] == target_code].copy()
                    detail_df['date_str'] = pd.to_datetime(detail_df[col_date]).dt.strftime('%y/%m/%d')
                    
                    final_res = detail_df[detail_df['date_str'] == selected_date][[col_date, col_seihin, col_qty]]
                    final_res.columns = ['要求日', '使用製品', '数量']

                    st.markdown(f'<div class="detail-area">', unsafe_allow_html=True)
                    st.markdown(f'#### 📋 {selected_date} の内訳 : {target_name} ({target_code})')
                    if not final_res.empty:
                        st.table(final_res)
                    else:
                        st.write("この日の個別要求はありません。")
                    st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1;'>データをアップロードしてください</p>", unsafe_allow_html=True)
