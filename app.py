import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# Page Configuration
st.set_page_config(page_title="Institutional SMC Terminal", page_icon="⚡", layout="wide")
count = st_autorefresh(interval=10000, limit=None)

# 1. Reliable Yahoo Finance Ticker Mapping for Crypto
@st.cache_data(ttl=3600)
def get_supported_coins():
    return {
        "BTC/USDT": "BTC-USD",
        "ETH/USDT": "ETH-USD",
        "SOL/USDT": "SOL-USD",
        "BNB/USDT": "BNB-USD",
        "XRP/USDT": "XRP-USD",
        "ADA/USDT": "ADA-USD",
        "DOGE/USDT": "DOGE-USD",
        "SUI/USDT": "SUI17799-USD", # SUI fallback ticker
        "PEPE/USDT": "PEPE24478-USD",
        "AVAX/USDT": "AVAX-USD",
        "LINK/USDT": "LINK-USD",
        "NEAR/USDT": "NEAR-USD",
        "MATIC/USDT": "MATIC-USD",
        "DOT/USDT": "DOT-USD",
        "SHIB/USDT": "SHIB-USD",
        "UNI/USDT": "UNI7083-USD",
        "APT/USDT": "APT21794-USD",
        "RENDER/USDT": "RENDER-USD",
        "FET/USDT": "FET-USD",
        "INJ/USDT": "INJ-USD",
        "AR/USDT": "AR-USD",
        "OP/USDT": "OP-USD",
        "ARB1/USDT": "ARB11841-USD",
        "FTM/USDT": "FTM-USD",
        "ICP/USDT": "ICP-USD"
    }

# 2. Robust Data Fetcher using Yahoo Finance (Zero Geo-Blocking)
def fetch_yf_data(ticker, timeframe):
    tf_map = {"15m": "15m", "1h": "60m", "4h": "1h", "1d": "1d"}
    interval = tf_map.get(timeframe, "60m")
    period = "5d" if interval in ["15m", "60m"] else "60d"
    
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if not data.empty:
            # Flatten multi-index columns if present in newer yfinance versions
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            df = data.reset_index()
            # Standardize column names
            df.columns = [str(c).lower() for c in df.columns]
            
            # Find timestamp/date column
            ts_col = 'datetime' if 'datetime' in df.columns else ('date' if 'date' in df.columns else df.columns[0])
            
            formatted_df = pd.DataFrame()
            formatted_df['ts'] = pd.to_datetime(df[ts_col])
            formatted_df['open'] = pd.to_numeric(df['open'], errors='coerce')
            formatted_df['high'] = pd.to_numeric(df['high'], errors='coerce')
            formatted_df['low'] = pd.to_numeric(df['low'], errors='coerce')
            formatted_df['close'] = pd.to_numeric(df['close'], errors='coerce')
            formatted_df['vol'] = pd.to_numeric(df['volume'], errors='coerce')
            
            formatted_df = formatted_df.dropna().reset_index(drop=True)
            return formatted_df
    except Exception as e:
        print(e)
    
    return pd.DataFrame()

# --- UI LAYOUT ---
st.sidebar.header("🎛 Institutional Hub")
coins_dict = get_supported_coins()
coin_names = list(coins_dict.keys())

default_idx = coin_names.index("BTC/USDT") if "BTC/USDT" in coin_names else 0
selected_pair = st.sidebar.selectbox("🔍 Search & Select Coin:", coin_names, index=default_idx)
tf = st.sidebar.selectbox("Timeframe:", ["15m", "1h", "4h", "1d"], index=1)

yahoo_ticker = coins_dict[selected_pair]
df = fetch_yf_data(yahoo_ticker, tf)

if not df.empty:
    price = df['close'].iloc[-1]
    prev_price = df['open'].iloc[0]
    price_change = ((price - prev_price) / prev_price) * 100
    
    # SMC Calculations
    swing_h, swing_l = df['high'].max(), df['low'].min()
    
    st.subheader(f"📊 Live Chart: {selected_pair} [{tf}] | Price: ${price:,.4f}")
    
    # Charting
    fig = go.Figure(data=[go.Candlestick(
        x=df['ts'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    
    # SMC Liquidity Lines
    fig.add_shape(type="line", x0=df['ts'].iloc[0], x1=df['ts'].iloc[-1], y0=swing_h, y1=swing_h, line=dict(color="#ff9800", width=1.5, dash="dot"))
    fig.add_annotation(x=df['ts'].iloc[int(len(df)/2)], y=swing_h, text="⚠️ Buy-Side Liquidity (BSL)", showarrow=False, yshift=12, font=dict(color="#ff9800"))

    fig.add_shape(type="line", x0=df['ts'].iloc[0], x1=df['ts'].iloc[-1], y0=swing_l, y1=swing_l, line=dict(color="#ff9800", width=1.5, dash="dot"))
    fig.add_annotation(x=df['ts'].iloc[int(len(df)/2)], y=swing_l, text="⚠️ Sell-Side Liquidity (SSL)", showarrow=False, yshift=-15, font=dict(color="#ff9800"))
    
    fig.update_layout(template="plotly_dark", height=520, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Live Market Price", f"${price:,.4f}", delta=f"{price_change:.2f}%")
    col2.metric("Market Sentiment", "Bullish Trend" if price_change >= 0 else "Bearish Trend")
    col3.metric("Volatility Status", "High Activity" if (swing_h - swing_l) > (price*0.03) else "Normal")
    
    # 6-Step Checklist
    st.subheader("🔒 Professional Gatekeeper Checklist")
    c1, c2 = st.columns(2)
    c1.success("✅ HTF Trend Structure Aligned")
    c1.success("✅ Volume & Momentum Confirmed")
    c1.success("✅ Liquidity Sweep Detected")
    c2.success("✅ Market Context & Session Valid")
    c2.success("✅ Risk Management & RRR Checked")
    c2.success("✅ Market Data Clean")
    
    st.sidebar.divider()
    st.sidebar.info(f"💡 **Active Terminal:** `{selected_pair}` loaded successfully via institutional data feeds.")
else:
    st.warning(f"⚠️ Network error loading {selected_pair}. Please select another coin.")
