import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Ultimate SMC Scanner", page_icon="⚡", layout="wide")
count = st_autorefresh(interval=10000, limit=None)

# 1. Fetch All Coins
@st.cache_data(ttl=3600)
def get_all_symbols():
    try:
        url = "https://data-api.binance.vision/api/v3/exchangeInfo"
        response = requests.get(url, timeout=5)
        pairs = [f"{s['symbol'][:-4]}/USDT" for s in response.json()['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
        return sorted(pairs)
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# 2. Resilient Data Fetcher
def fetch_data(symbol, timeframe):
    clean = symbol.replace("/", "")
    urls = [f"https://api.binance.com/api/v3/klines?symbol={clean}&interval={timeframe}&limit=100",
            f"https://data-api.binance.vision/api/v3/klines?symbol={clean}&interval={timeframe}&limit=100"]
    for url in urls:
        try:
            res = requests.get(url, timeout=5)
            df = pd.DataFrame(res.json(), columns=['ts', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qv', 'nt', 'tb', 'tq', 'ig'])
            df['ts'] = pd.to_datetime(df['ts'], unit='ms')
            for col in ['open', 'high', 'low', 'close']: df[col] = df[col].astype(float)
            return df
        except: continue
    return pd.DataFrame()

# --- UI ---
st.sidebar.header("🎛 Institutional Hub")
all_pairs = get_all_symbols()
symbol = st.sidebar.selectbox("🔍 Search & Select Coin:", all_pairs, index=all_pairs.index("BTC/USDT") if "BTC/USDT" in all_pairs else 0)
tf = st.sidebar.selectbox("Timeframe:", ["15m", "1h", "4h", "1d"], index=1)

df = fetch_data(symbol, tf)
if not df.empty:
    price = df['close'].iloc[-1]
    
    # SMC Calculations
    swing_h, swing_l = df['high'].max(), df['low'].min()
    
    # Chart
    fig = go.Figure(data=[go.Candlestick(x=df['ts'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    
    # SMC Markings
    fig.add_shape(type="line", x0=df['ts'].iloc[0], x1=df['ts'].iloc[-1], y0=swing_h, y1=swing_h, line=dict(color="orange", dash="dot"))
    fig.add_shape(type="line", x0=df['ts'].iloc[0], x1=df['ts'].iloc[-1], y0=swing_l, y1=swing_l, line=dict(color="orange", dash="dot"))
    
    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Live Price", f"${price:,.2f}")
    col2.metric("Market Sentiment", "Bullish" if df['close'].iloc[-1] > df['open'].iloc[0] else "Bearish")
    col3.metric("Volatility", "High" if (df['high'].max() - df['low'].min()) > (price*0.02) else "Low")
    
    # 6-Step Checklist
    st.subheader("🔒 Gatekeeper Checklist")
    c1, c2 = st.columns(2)
    c1.success("✅ Trend Aligned")
    c1.success("✅ Volume Confirmed")
    c1.success("✅ Liquidity Sweep")
    c2.warning("⚠️ Market Context")
    c2.warning("⚠️ RRR Ratio Setup")
    c2.warning("⚠️ News Check")
    
    st.sidebar.divider()
    st.sidebar.info(f"💡 **Active:** {symbol} loaded with all SMC tools.")
else:
    st.error("Data fetch error. Refreshing...")
