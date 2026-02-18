# (app.py の dataframe 表示部分)
st.dataframe(
    # na_rep="0.000" を指定することで、万が一のNoneも0として表示
    df_result.style.applymap(color_negative_red).format(precision=3, na_rep="0.000"),
    use_container_width=True,
    height=800,
    hide_index=True,
    column_config={
        "品番": st.column_config.TextColumn("品番", pinned=True),
        "品名": st.column_config.TextColumn("品名", pinned=True),
    }
)
