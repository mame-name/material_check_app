import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# --- デザイン設定 ---
st.set_page_config(layout="wide", page_title="生産管理システム")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .detail-area {
        background-color: #ffffff; border: 2px solid #1f77b4;
        border-radius: 10px; padding: 20px; margin-top: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- サイドバー ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み設定")
    if st.session_state.get('req'):
        try:
            df_req_raw = pd.read_excel(st.session_state.req, header=3)
            df_req_raw.columns = df_req_raw.columns.str.strip()
            product_options = ["全表示"] + sorted(df_req_raw.iloc[:, 7].dropna().unique().tolist())
        except: product_options = ["全表示"]
    else: product_options = ["全表示"]

    st.selectbox("製品名選択", options=product_options, key="selected_product")
    end_date = st.date_input("終了日", value=(datetime.now() + timedelta(days=14)).date())
    end_date_str = end_date.strftime('%y/%m/%d')
    show_shortage_only = st.toggle("🚨 不足原料のみを表示")

    st.divider()
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")

# --- メインエリア ---
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
            matched_materials = df_req[df_req.iloc[:, 7] == st.session_state.selected_product].iloc[:, 2].unique().tolist()
            display_df = display_df[display_df['品番'].isin(matched_materials) | (display_df['品番'] == "")]

        plot_df = display_df.copy().reset_index(drop=True)
        plot_df['前日在庫'] = plot_df['前日在庫'].astype(object)
        plot_df.loc[plot_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        st.info("💡 「要求量」の行の数字をクリックして内訳を表示")
        
        event = st.dataframe(
            plot_df.style.applymap(lambda v: 'color:red;font-weight:bold;' if isinstance(v,(int,float)) and v<0 else None).format(precision=3),
            use_container_width=True, height=400, hide_index=True,
            on_select="rerun", selection_mode="single-cell"
        )

        # --- 内訳表示ロジック（スリム版） ---
        if event and len(event.selection.cells) > 0:
            cell = event.selection.cells[0]
            r_val = cell.get('row') if isinstance(cell, dict) else cell[0]
            c_val = cell.get('column') if isinstance(cell, dict) else cell[1]
            r_idx = int(r_val[0] if isinstance(r_val, list) else r_val)
            
            if isinstance(c_val, str): selected_date_str = c_val
            else: selected_date_str = plot_df.columns[int(c_val[0] if isinstance(c_val, list) else c_val)]

            row_data = plot_df.iloc[r_idx]

            if row_data['区分'] == '要求量 (ー)' and selected_date_str not in fixed_cols:
                target_code = str(row_data['品番']).strip()
                
                # 所要量一覧から抽出
                # 2:品番, 5:要求日, 7:要求元品名, 11:基準単位数量
                d_hinban = df_req.iloc[:, 2].astype(str).str.strip()
                detail_df = df_req[d_hinban == target_code].copy()
                detail_df['temp_date'] = pd.to_datetime(detail_df.iloc[:, 5], errors='coerce').dt.strftime('%y/%m/%d')
                
                res = detail_df[detail_df['temp_date'] == selected_date_str].copy()
                
                st.markdown('<div class="detail-area">', unsafe_allow_html=True)
                st.markdown(f"#### 📋 {selected_date_str} の内訳 : {row_data['品名']}")
                
                if not res.empty:
                    # 5:要求日, 7:要求元品名, 11:基準単位数量
                    view_df = res.iloc[:, [7, 11]].copy()
                    view_df.columns = ['使用製品名', '数量']
                    
                    # 同じ製品があれば数量を合算
                    view_df = view_df.groupby(['使用製品名'])['数量'].sum().reset_index()
                    
                    # インデックスを隠して表示
                    st.dataframe(view_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("この日の明細データが見つかりませんでした。")
                st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.write("データをアップロードしてください。")
