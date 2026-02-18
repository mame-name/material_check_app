# (app.py の col2 部分)
with col2:
    st.header("📋 シミュレーション結果")
    
    if file_req and file_inv:
        try:
            df_req = pd.read_excel(file_req, header=3)
            df_inv = pd.read_excel(file_inv, header=4)
            
            df_sim = process_files_and_create_sim(df_req, df_inv)
            
            # マイナスを赤字にする
            def color_negative_red(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red'
                return None

            st.dataframe(
                df_sim.style.applymap(color_negative_red),
                use_container_width=True,
                height=700,
                hide_index=True
            )
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
    else:
        st.info("左側で「所要量」と「在庫」の2つのファイルをアップロードしてください。")
