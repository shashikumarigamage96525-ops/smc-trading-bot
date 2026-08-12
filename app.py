import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Professional Trading Terminal", layout="wide")

# Live auto-refresh every 5 seconds
st_autorefresh(interval=5000, limit=None, key="live_counter")

st.title("⚡ Professional Trading Terminal (Live & Interactive)")

# 1. Fetch Real Binance Data
@st.cache_data(ttl=10)
def fetch_binance_data(symbol):
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval=1h&limit=200"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return None
        
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'a', 'b', 'c', 'd', 'e', 'f'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        return df
    except:
        return None

# 2. Sidebar Controls
symbol = st.sidebar.selectbox("Select Trading Pair", ["BTC/USDT", "ETH/USDT", "ADA/USDT", "SOL/USDT", "BCH/USDT"], index=0)
df = fetch_binance_data(symbol)

if df is not None and not df.empty:
    current_price = df['close'].iloc[-1]
    
    st.sidebar.divider()
    st.sidebar.subheader("💰 Account & Position Sizing")
    account_balance = st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0)
    risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

    st.sidebar.divider()
    st.sidebar.subheader("📈 Trade Setup Configuration")
    trade_type = st.sidebar.radio("Direction Strategy:", ["LONG (Bullish)", "SHORT (Bearish)"], horizontal=True)

    p_step = 0.0001 if current_price < 10 else 0.1
    
    # Default values based on live price
    def_sl = current_price * 0.99 if "LONG" in trade_type else current_price * 1.01
    def_tp = current_price * 1.02 if "LONG" in trade_type else current_price * 0.98

    entry_price = st.sidebar.number_input("Entry Price:", value=float(current_price), format="%.4f", step=p_step)
    sl_price = st.sidebar.number_input("Stop Loss (SL):", value=float(def_sl), format="%.4f", step=p_step)
    tp_price = st.sidebar.number_input("Take Profit (TP):", value=float(def_tp), format="%.4f", step=p_step)

    risk_amount_usd = account_balance * (risk_percentage / 100.0)
    price_risk_per_unit = abs(entry_price - sl_price)
    position_size_units = risk_amount_usd / price_risk_per_unit if price_risk_per_unit > 0 else 0

    st.sidebar.info(f"💡 **Position Sizing:** Risk: **${risk_amount_usd:.2f}** | Size: **{position_size_units:,.2f} units**")

    # 3. Main Dashboard Layout
    col1, col2 = st.columns([3, 1])

    with col1:
        trend_status = "🟢 BULLISH (Above EMA)" if current_price > df['EMA_50'].iloc[-1] else "🔴 BEARISH (Below EMA)"
        st.write(f"### Live Chart: {symbol} [1h]")
        st.info(f"📊 **Trend Structure:** {trend_status} | **Live Market Price:** `${current_price:,.4f}`")

        # Plotly Candlestick Chart
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350', name='Candles'
        )])

        # EMAs
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], name='EMA 50', line=dict(color='#2196f3', width=1.5)))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], name='EMA 200', line=dict(color='#ff9800', width=1.5)))

        # --- ENTRY, SL, TP LINES ON CHART ---
        t_label = "LONG" if "LONG" in trade_type else "SHORT"
        
        # Entry Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=entry_price, y1=entry_price,
                    line=dict(color="#2196f3", width=2, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=entry_price, text=f"ENTRY: {entry_price}", showarrow=True, arrowhead=1, ax=-40, ay=0, bgcolor="#2196f3", font=dict(color="white"))

        # Stop Loss Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price,
                    line=dict(color="#f44336", width=2, dash="dash"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl_price, text=f"SL: {sl_price}", showarrow=True, arrowhead=1, ax=-40, ay=15, bgcolor="#f44336", font=dict(color="white"))

        # Take Profit Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp_price, y1=tp_price,
                    line=dict(color="#4caf50", width=2, dash="dash"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp_price, text=f"TP: {tp_price}", showarrow=True, arrowhead=1, ax=-40, ay=-15, bgcolor="#4caf50", font=dict(color="white"))

        fig.update_layout(
            height=600,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📌 Trade Metrics")
        st.metric(label="Live Market Price", value=f"${current_price:,.4f}")
        st.metric(label="Account Risk ($)", value=f"${risk_amount_usd:,.2f}")
        st.metric(label="Calculated Units", value=f"{position_size_units:,.2f}")
        
        rrr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0
        st.divider()
        st.success(f"📌 **Strategy:** {t_label}\n\n🎯 **RRR Ratio:** 1:{rrr:.2f}")

else:
    st.error("බයිනෑන්ස් වෙතින් ලයිව් දත්ත ලබා ගැනීමට නොහැකි විය. කරුණාකර මොහොතަކින් නැවත උත්සාහ කරන්න.")
