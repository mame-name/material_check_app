import streamlit as st
import pandas as pd
from calc import create_pivot

st.set_page_config(layout="wide", page_title="生産管理システム")

# --- UIデザイン（2画面独立スクロール ＋ アップローダーの薄型化） ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    /* 左カラム：操作パネル（固定） */
    [data-testid="stColumn"]:nth-child(1) {
        position: sticky;
        top: 0;
        height: 100vh;
        overflow-y: auto;
        background-color: #ffffff;
        padding: 2rem;
        border-right: 2px solid #e9ecef;
    }
    /* 右カラム：表示エリア（独立スクロール） */
    [data-testid="stColumn"]:nth-child(2) {
        height: 100vh;
        overflow-y: auto;
        padding: 2rem;
        background-color: #f8f9fa;
    }
    header {visibility: hidden;}
    #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
    
    /* --- アップローダーの薄型化 ＋ 注釈(Limit 200MB...)の非表示 --- */
    .stFileUploader { border: 1px solid #e6e9ef; border-radius: 10px; padding: 5px; }
    
    [data-testid="stFileUploaderSmallNumber"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }
    [data-testid="stFileUploader"] section {
        padding: 0px 10px !important;
        min-height: 50px !important;
    }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("##### 📁 データ読込")
    file_req = st.file_uploader("1. 所要量一覧表を選択", type=['xlsx', 'xls'], key="req")
    file_inv = st.file_uploader("2. 在庫一覧表を選択", type=['xlsx', 'xls'], key="inv")
    file_ord = st.file_uploader("3. 発注リストを選択", type=['xlsx', 'xls'], key="ord")
    
    st.divider()
    # --- 製品コード入力欄の追加 ---
    target_product_code = st.text_input("🔍 絞り込み製品コード", placeholder="例: 010101")
    
    st.divider()
    st.caption("3つのファイルを読み込むと計算を開始します。製品コードを入力すると特定の原料に絞り込めます。")

with col2:
    st.markdown("<h1 style='text-align: center;'>原料在庫シミュレーション</h1>", unsafe_allow_html=True)
    st.markdown("---")

    if file_req and file_inv and file_ord:
        try:
            # データの読み込み
            # 所要量一覧表（品番検索用と計算用）
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            df_ord = pd.read_excel(file_ord, header=4)

            # --- 製品コードによるフィルタリングロジック ---
            display_df = None
            
            if target_product_code:
                # G列（製品コード）から一致する行を探し、C列（品番）を取得
                # pd.read_excelのheader=3により、列名はExcelの4行目の値になります。
                # 列名が直接指定できない場合を考慮し、列番号（G=index 6, C=index 2）で処理します
                
                # 型の不一致を防ぐため文字列として比較
                df_req.columns = df_req.columns.str.strip()
                
                # G列（製品コード）とC列（品番）の列名を取得（動的対応）
                col_g = df_req.columns[6] # G列
                col_c = df_req.columns[2] # C列
                
                # 入力された製品コードに一致する品番(原料)のリストを取得
                matched_materials = df_req[df_req[col_g].astype(str) == str(target_product_code)][col_c].unique()
                
                if len(matched_materials) > 0:
                    # 計算実行（元データ）
                    df_result = create_pivot(df_req, df_inv, df_ord)
                    
                    # 計算結果から、一致した品番のみを抽出
                    display_df = df_result[df_result['品番'].isin(matched_materials)]
                else:
                    st.warning(f"製品コード「{target_product_code}」が見つかりません。")
            else:
                # 製品コード未入力の場合は全表示
                display_df = create_pivot(df_req, df_inv, df_ord)

            # スタイル定義
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return None

            # データフレーム表示
            if display_df is not None and not display_df.empty:
                st.dataframe(
                    display_df.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
                    use_container_width=True,
                    height=1000,
                    hide_index=True,
                    column_config={
                        "品番": st.column_config.TextColumn("品番", pinned=True),
                        "品名": st.column_config.TextColumn("品名", pinned=True),
                    }
                )
            elif target_product_code:
                st.info("該当する原料の推移データがありません。")
            
        except Exception as e:
            st.error(f"解析エラーが発生しました: {e}")
    else:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #d1d1d1;'>左側のパネルからデータをアップロードしてください</p>", unsafe_allow_html=True)
