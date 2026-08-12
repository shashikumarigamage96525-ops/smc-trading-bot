import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# Page Configuration
st.set_page_config(page_title="Binance Global Terminal", page_icon="⚡", layout="wide")
count = st_autorefresh(interval=10000, limit=None, key="live_price_counter")

# 1. Fetch ALL USDT Pairs from Binance (Real-Time)
@st.cache_data(ttl=3600)
def get_all_usdt_pairs():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        data = response.json()
        # Filter all symbols ending in USDT and active
        pairs = [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
        # Convert to standard format BTCUSDT -> BTC/USDT
        formatted = [f"{s[:-4]}/USDT" for s in pairs]
        return sorted(formatted)
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# 2. Fetch Chart Data
def fetch_chart_data(symbol, timeframe='1h', limit=100):
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}"
        response = requests.get(url, timeout=5)
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'c_time', 'q_vol', 'n_trades', 'tb_base', 'tb_quote', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close']: df[col] = df[col].astype(float)
        return df
    except:
        return pd.DataFrame()

# --- UI LAYOUT ---
st.title("⚡ Binance Global Institutional Scanner")

# Searchable Dropdown for EVERY Coin
all_pairs = get_all_usdt_pairs()
selected_coin = st.sidebar.selectbox(
    "🔍 Type & Search Any Coin (Binance USDT Pairs):", 
    all_pairs, 
    index=all_pairs.index("BTC/USDT") if "BTC/USDT" in all_pairs else 0
)

timeframe = st.sidebar.selectbox("Timeframe:", ["5m", "15m", "1h", "4h", "1d"], index=2)

# --- DISPLAY SECTION ---
df = fetch_chart_data(selected_coin, timeframe)

if not df.empty:
    st.subheader(f"📊 Live Chart: {selected_coin}")
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Quick Metrics
    last_price = df['close'].iloc[-1]
    st.metric(label=f"Current {selected_coin} Price", value=f"${last_price:,.4f}")
else:
    st.error("Could not fetch data for this pair. Please try again.")

st.info("💡 **Tip:** Sidebar එකේ උඩින්ම තියෙන පෙට්ටියට ඕනෑම coin එකක් (උදා: ADA, XRP, PEPE) Type කරලා select කරන්න පුළුවන්. මුළු Binance එකේම USDT pairs ඔක්කොම මෙතන තියෙනවා.")
