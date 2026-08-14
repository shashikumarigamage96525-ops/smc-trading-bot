# ============================================================
# TRADE JOURNAL (Continued)
# ============================================================
st.subheader(
    "📔 Institutional Trade Journal"
)

with st.form("journal_form"):
    
    j_col1, j_col2, j_col3 = st.columns(3)
    
    with j_col1:
        journal_asset = st.selectbox(
            "Asset",
            symbols,
            index=symbols.index(selected_coin) if selected_coin in symbols else 0
        )
        journal_type = st.selectbox(
            "Type",
            ["LONG 🟢", "SHORT 🔴"]
        )
        
    with j_col2:
        journal_entry = st.number_input(
            "Execution Price",
            value=float(entry_price),
            format="%.6f"
        )
        journal_exit = st.number_input(
            "Exit Price",
            value=float(tp1_price),
            format="%.6f"
        )
        
    with j_col3:
        journal_size = st.number_input(
            "Position Size (Units)",
            value=float(position_size),
            format="%.4f"
        )
        journal_outcome = st.selectbox(
            "Outcome",
            ["WIN 🟢", "LOSS 🔴", "BREAKEVEN ⚪", "OPEN ⏳"]
        )

    journal_notes = st.text_area(
        "Trade Thesis / Psychological Notes",
        placeholder="Enter confluence factors, market context, or mental state..."
    )

    submit_journal = st.form_submit_button(
        "💾 Save to Trade Journal"
    )

    if submit_journal:
        
        # Calculate P&L estimate
        if "LONG" in journal_type:
            pnl_usd = (journal_exit - journal_entry) * journal_size
        else:
            pnl_usd = (journal_entry - journal_exit) * journal_size

        st.session_state.trade_journal.append(
            {
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Asset": journal_asset,
                "Type": journal_type,
                "Entry": journal_entry,
                "Exit": journal_exit,
                "Size": journal_size,
                "Outcome": journal_outcome,
                "P&L ($)": round(pnl_usd, 2),
                "Notes": journal_notes
            }
        )
        
        st.success("Trade successfully recorded in your institutional journal.")

if st.session_state.trade_journal:
    
    journal_df = pd.DataFrame(
        st.session_state.trade_journal
    )
    
    # Summary Metrics for Journal
    total_trades = len(journal_df)
    closed_trades = journal_df[journal_df["Outcome"] != "OPEN ⏳"]
    
    if not closed_trades.empty:
        wins = len(closed_trades[closed_trades["Outcome"] == "WIN 🟢"])
        win_rate = (wins / len(closed_trades)) * 100
        total_pnl = closed_trades["P&L ($)"].sum()
    else:
        win_rate = 0.0
        total_pnl = 0.0

    jc1, jc2, jc3 = st.columns(3)
    jc1.metric("Total Journaled Trades", total_trades)
    jc2.metric("Closed Win Rate", f"{win_rate:.1f}%")
    jc3.metric("Cumulative P&L", f"${total_pnl:,.2f}")

    st.dataframe(
        journal_df,
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("🗑️ Clear Trade Journal"):
        st.session_state.trade_journal = []
        st.rerun()

else:
    st.info("No trades logged in the journal yet. Record your executions above.")
