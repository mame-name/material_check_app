import streamlit as st
import pandas as pd
from calc import create_pivot
from datetime import datetime, timedelta

# --- 1. ページ設定 & UIデザイン（以前の完成形を維持） ---
st.set_page_config(layout="wide", page_title="生産管理システム")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e9ecef;
    }
    header {visibility: hidden;}

    /* 入力エリアの青枠デザイン */
    div[data-baseweb="select"], 
    div[data-baseweb="date-input-container"],
    div[data-testid="stDateInput"] > div {
        border: 2px solid #1f77b4 !important;
        border-radius: 5px !important;
        background-color: white !important;
        margin-bottom: 20px;
    }

    /* 内訳表示用のフローティングパネル風デザイン */
    .floating-panel {
        background-color: #ffffff;
        border: 2px solid #1f77b4;
        border-radius: 10px;
        padding: 15px;
        margin-top: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# セッション状態の初期化
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = "全表示"

# --- 2. 左画面（サイドバー）：操作パネル ---
with st.sidebar:
    st.markdown("### 🔍 絞り込み設定")
    
    product_options = ["全表示"]
    if st.session_state.get('req'):
        try:
            # 7番目の列から製品名を取得
            df_req_raw = pd.read_excel(st.session_state.req, header=3)
            df_req_raw.columns = df_req_raw.columns.str.strip()
            product_options += sorted(df_req_raw.iloc[:, 7].dropna().unique().tolist())
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

# --- 3. 右画面（メインエリア）：結果表示 ---
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>原料在庫シミュレーション</h3>", unsafe_allow_html=True)

if st.session_state.get('req') and st.session_state.get('inv') and st.session_state.get('ord'):
    try:
        # Excel読み込み
        df_req = pd.read_excel(st.session_state.req, header=3)
        df_inv = pd.read_excel(st.session_state.inv, header=4)
        df_ord = pd.read_excel(st.session_state.ord, header=4)
        df_req.columns = df_req.columns.str.strip()
        
        # calc.pyのロジックで計算
        df_raw_result = create_pivot(df_req, df_inv, df_ord)
        
        if '現在庫' in df_raw_result.columns:
            df_raw_result = df_raw_result.rename(columns={'現在庫': '前日在庫'})
        
        # 列の絞り込み
        fixed_cols = ['品番', '品名', '区分', '前日在庫']
        target_date_cols = [c for c in df_raw_result.columns if c not in fixed_cols and c <= end_date_str]
        display_df = df_raw_result[fixed_cols + target_date_cols].copy()

        # フィルタ処理：製品名
        if st.session_state.selected_product != "全表示":
            matched_materials = df_req[df_req.iloc[:, 7] == st.session_state.selected_product].iloc[:, 2].unique().tolist()
            # 品番が一致する行、または3行1セットを維持するための空行を保持
            display_df = display_df[display_df['品番'].isin(matched_materials) | (display_df['品番'] == "")]

        # フィルタ処理：不足原料
        if show_shortage_only:
            stock_rows = display_df[display_df['区分'] == '在庫残 (＝)']
            if target_date_cols:
                shortage_mask = (stock_rows[target_date_cols] < 0).any(axis=1)
                shortage_indices = stock_rows[shortage_mask].index
                all_short_idx = []
                for idx in shortage_indices: all_short_idx.extend([idx-2, idx-1, idx])
                display_df = display_df.loc[display_df.index.intersection(all_short_idx)]

        plot_df = display_df.copy().reset_index(drop=True)
        # 前日在庫の表示制御
        plot_df['前日在庫'] = plot_df['前日在庫'].astype(object)
        plot_df.loc[plot_df['区分'] != '要求量 (ー)', '前日在庫'] = ""

        st.info("💡 「要求量」の数字をクリックすると、その日の製品別内訳が表示されます")

        # --- メインテーブル表示 (セル選択モード) ---
        event = st.dataframe(
            plot_df.style.applymap(lambda v: 'color:red;font-weight:bold;' if isinstance(v,(int,float)) and v<0 else None).format(precision=3),
            use_container_width=True, height=500, hide_index=True,
            on_select="rerun", selection_mode="single-cell"
        )

        # --- 4. 内訳表示ロジック (ポップアップ風) ---
        if event and len(event.selection.cells) > 0:
            cell = event.selection.cells[0]
            # 座標取得 (辞書/タプル両対応)
            r_val = cell.get('row') if isinstance(cell, dict) else cell[0]
            c_val = cell.get('column') if isinstance(cell, dict) else cell[1]
            r_idx = int(r_val[0] if isinstance(r_val, list) else r_val)
            
            # 列名の特定
            if isinstance(c_val, str): 
                selected_date_str = c_val
            else: 
                selected_date_str = plot_df.columns[int(c_val[0] if isinstance(c_val, list) else c_val)]

            row_data = plot_df.iloc[r_idx]

            # 「要求量」の行がクリックされた時のみ詳細を出す
            if row_data['区分'] == '要求量 (ー)' and selected_date_str not in fixed_cols:
                target_code = str(row_data['品番']).strip()
                
                # 所要量一覧から対象品番を抽出
                # 2:品番, 5:要求日, 7:要求元品名, 11:基準単位数量
                d_hinban = df_req.iloc[:, 2].astype(str).str.strip()
                detail_df = df_req[d_hinban == target_code].copy()
                
                # 日付の一致確認 (年月日のみ比較)
                detail_df['temp_date'] = pd.to_datetime(detail_df.iloc[:, 5], errors='coerce').dt.strftime('%y/%m/%d')
                res = detail_df[detail_df['temp_date'] == selected_date_str].copy()
                
                # パネル表示
                st.markdown(f'<div class="floating-panel">', unsafe_allow_html=True)
                st.markdown(f"#### 📋 {selected_date_str} の内訳 : {row_data['品名']}")
                
                if not res.empty:
                    view_df = res.iloc[:, [7, 11]].copy()
                    view_df.columns = ['使用製品名', '数量']
                    # 製品名ごとに合算
                    view_df = view_df.groupby(['使用製品名'])['数量'].sum().reset_index()
                    
                    st.dataframe(view_df, use_container_width=True, hide_index=True)
                    if st.button("✕ 閉じる"):
                        st.rerun()
                else:
                    st.warning("明細データが見つかりませんでした。")
                st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"解析エラーが発生しました: {e}")
else:
    st.markdown("<br><br><br><p style='text-align: center; color: #d1d1d1;'>データをアップロードしてください</p>", unsafe_allow_html=True)
