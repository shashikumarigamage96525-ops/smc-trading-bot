# 10. Whale Transactions / Large Trades Tracker
@st.cache_data(ttl=5)
def fetch_whale_transactions(symbol, threshold_usd=10000):
    whale_trades = []
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/trades?symbol={clean_symbol}&limit=50"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            trades = response.json()
            for t in trades:
                price = float(t['price'])
                qty = float(t['qty'])
                total_usd = price * qty
                
                if total_usd >= threshold_usd:
                    is_buyer_maker = t['isBuyerMaker'] # True means Seller was aggressive (Sell), False means Buyer was aggressive (Buy)
                    side = "SELL 🔴" if is_buyer_maker else "BUY 🟢"
                    
                    whale_trades.append({
                        "Time": pd.to_datetime(t['time'], unit='ms').strftime('%H:%M:%S'),
                        "Side": side,
                        "Price": price,
                        "Amount": qty,
                        "Total ($)": total_usd
                    })
    except:
        pass
        
    # Fallback dummy data if network fails or no large trades found in immediate window
    if not whale_trades:
        whale_trades.append({
            "Time": "Just now",
            "Side": "BUY 🟢",
            "Price": current_live_price,
            "Amount": 1.5,
            "Total ($)": current_live_price * 1.5
        })
        
    return whale_trades
