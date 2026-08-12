import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Institutional Trading Terminal",
    page_icon="⚡",
    layout="wide"
)

count = st_autorefresh(interval=5000, limit=None, key="live_price_counter")

@st.cache_data(ttl=300)
def fetch_available_coins():
    return [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", 
        "ADA/USDT", "DOGE/USDT", "SUI/USDT", "PEPE/USDT", "AVAX/USDT",
        "LINK/USDT", "NEAR/USDT", "MATIC/USDT", "DOT/USDT", "SHIB/USDT"
    ]

def fetch_chart_data(symbol, timeframe='1h', limit=100):
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            url = f"https://data-api.binance.vision/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}"
            response = requests.get(url, timeout=5)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def calculate_indicators(df):
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def advanced_pattern_recognition(df):
    if df.empty or len(df) < 30:
        return [], []
    highs = df['high'].values
    lows = df['low'].values
    supports, resistances = [], []
    for i in range(3, len(df) - 3):
        if highs[i] == max(highs[i-3:i+3]):
            resistances.append(highs[i])
        if lows[i] == min(lows[i-3:i+3]):
            supports.append(lows[i])
    return sorted(list(set(supports)))[:2], sorted(list(set(resistances)))[-2:]

# --- UI LAYOUT ---
st.title("⚡ Mobile Trading Terminal")

all_symbols = fetch_available_coins()
selected_coin = st.sidebar.selectbox("🔍 Select Pair:", all_symbols, index=0)
timeframe = st.sidebar.selectbox("Select Timeframe:", ["15m", "1h", "4h"], index=1)

df_initial = fetch_chart_data(selected_coin, timeframe=timeframe)
current_live_price = df_initial['close'].iloc[-1] if not df_initial.empty else 1.0
supports, resistances = advanced_pattern_recognition(df_initial)

st.sidebar.divider()
account_balance = st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0)
risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0)

# Auto S&R calculations for clean signal execution
if supports and resistances:
    nearest_support = supports[-1]
    nearest_resistance = resistances[0]
    if (current_live_price - nearest_support) < (nearest_resistance - current_live_price):
        trade_type = "LONG (Bullish)"
        entry_price = current_live_price
        sl_price = nearest_support * 0.992
        tp_price = entry_price + (abs(entry_price - sl_price) * 3)
    else:
        trade_type = "SHORT (Bearish)"
        entry_price = current_live_price
        sl_price = nearest_resistance * 1.008
        tp_price = entry_price - (abs(sl_price - entry_price) * 3)
else:
    trade_type = "LONG (Bullish)"
    entry_price = current_live_price
    sl_price = current_live_price * 0.98
    tp_price = current_live_price * 1.06

risk_amount_usd = account_balance * (risk_percentage / 100.0)
price_risk_per_unit = abs(entry_price - sl_price)
position_size_units = risk_amount_usd / price_risk_per_unit if price_risk_per_unit > 0 else 0
rrr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0

st.sidebar.info(f"💡 **Risk:** ${risk_amount_usd:.2f} | **Units:** {position_size_units:,.2f} | **RRR:** 1:{rrr:.2f}")

# --- MAIN CHART AREA ---
df = fetch_chart_data(selected_coin, timeframe=timeframe)
if not df.empty:
    df = calculate_indicators(df)
    live_price = df['close'].iloc[-1]
    
    st.markdown(f"### 📊 {selected_coin} [{timeframe}] — Live: **${live_price:,.4f}**")
    
    # Optimized Plotly Chart for Mobile Viewing (Fixed aspect & padding)
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#00E676', decreasing_line_color='#FF5252',
        name='Price'
    )])
    
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#29B6F6', width=1)))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#FFA726', width=1.2)))
    
    # Support / Resistance Lines
    for sup in supports:
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sup, y1=sup, line=dict(color="#00C853", width=1, dash="dot"))
    for res in resistances:
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=res, y1=res, line=dict(color="#D50000", width=1, dash="dot"))

    # Entry, SL, TP Lines
    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=entry_price, y1=entry_price, line=dict(color="#29B6F6", width=1.5, dash="dash"))
    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price, line=dict(color="#FF5252", width=1.5, dash="dash"))
    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp_price, y1=tp_price, line=dict(color="#00E676", width=1.5, dash="dash"))

    # Clean Mobile Layout Configuration
    fig.update_layout(
        height=450, # Reduced height so it fits well on phone screens without vertical stretching
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        xaxis_rangeslider_visible=False,
        margin=dict(l=5, r=5, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.success(f"🟢 **Strategy:** {trade_type} | **Entry:** ${entry_price:,.2f} | **SL:** ${sl_price:,.2f} | **TP:** ${tp_price:,.2f}")
else:
    st.warning("Loading data...")
