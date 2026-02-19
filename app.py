import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# --- デザイン設定 ---
st.set_page_config(layout="wide", page_title="生産管理システム")
st.markdown("""
    <style>
    /* 詳細エリアを「浮いているパネル」のように見せるCSS */
    .floating-panel {
        background-color: #ffffff;
        border: 1px solid #1f77b4;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        position: relative;
        z-index: 1000;
        margin-top: -10px;
    }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- サイドバー (データ読込・フィルタ) ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み")
    # (中略: 以前と同じ読み込み処理)
    st.file_uploader("1. 所要量一覧表", type=['xlsx', 'xls'], key="req")
    st.file_uploader("2. 発注リスト", type=['xlsx', 'xls'], key="ord")
    st.file_uploader("3. 在庫一覧表", type=['xlsx', 'xls'], key="inv")
    
    # 終了日指定
    end_date = st.date_input("終了日", value=(datetime.now() + timedelta(days=14)).date())
    end_date_str = end_date.strftime('%y/%m/%d')

# --- メインエリア ---
if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        # データ読込
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        # ピボット計算
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
        plot_df = df_raw_result[fixed_cols + target_date_cols].copy().reset_index(drop=True)
        
        st.subheader("📊 原料在庫シミュレーション")

        # --- 表の表示 ---
        event = st.dataframe(
            plot_df.style.applymap(lambda v: 'color:red;font-weight:bold;' if isinstance(v,(int,float)) and v<0 else None).format(precision=3),
            use_container_width=True, height=450, hide_index=True,
            on_select="rerun", selection_mode="single-cell"
        )

        # --- 選択された際の内訳表示 (ポップアップ風) ---
        if event and len(event.selection.cells) > 0:
            cell = event.selection.cells[0]
            r_val = cell.get('row') if isinstance(cell, dict) else cell[0]
            c_val = cell.get('column') if isinstance(cell, dict) else cell[1]
            r_idx = int(r_val[0] if isinstance(r_val, list) else r_val)
            
            if isinstance(c_val, str): selected_date_str = c_val
            else: selected_date_str = plot_df.columns[int(c_val[0] if isinstance(c_val, list) else c_val)]

            row_data = plot_df.iloc[r_idx]

            # 要求量行のみ反応
            if row_data['区分'] == '要求量 (ー)' and selected_date_str not in fixed_cols:
                target_code = str(row_data['品番']).strip()
                
                # 検索と集計
                d_hinban = df_req.iloc[:, 2].astype(str).str.strip()
                detail_df = df_req[d_hinban == target_code].copy()
                detail_df['temp_date'] = pd.to_datetime(detail_df.iloc[:, 5], errors='coerce').dt.strftime('%y/%m/%d')
                res = detail_df[detail_df['temp_date'] == selected_date_str].copy()

                # --- 浮遊パネル風の表示エリア ---
                with st.container():
                    st.markdown(f"""
                        <div class="floating-panel">
                            <h4 style="margin-top:0; color:#1f77b4;">🔍 {selected_date_str} 内訳明細</h4>
                            <p style="font-size:0.9rem; color:#666;"><b>品番:</b> {target_code}　<b>品名:</b> {row_data['品名']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if not res.empty:
                        view_df = res.iloc[:, [7, 11]].copy()
                        view_df.columns = ['使用製品名', '数量']
                        view_df = view_df.groupby(['使用製品名'])['数量'].sum().reset_index()
                        
                        # 浮遊パネルの中にテーブルを配置
                        st.dataframe(view_df, use_container_width=True, hide_index=True)
                        
                        # パネルを閉じるためのボタン（再実行で選択解除）
                        if st.button("✕ 閉じる"):
                            st.rerun()
                    else:
                        st.write("明細がありません")
                    st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"エラー: {e}")
else:
    st.info("左側からファイルをアップロードしてください。")
