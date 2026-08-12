import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# Page Configuration
st.set_page_config(page_title="Binance Global Terminal", page_icon="⚡", layout="wide")
count = st_autorefresh(interval=10000, limit=None, key="live_price_counter")

# 1. Reliable Coin List (Expanded with Top Coins + Fallback)
@st.cache_data(ttl=3600)
def get_all_usdt_pairs():
    try:
        # Trying public Binance exchange info
        url = "https://data-api.binance.vision/api/v3/exchangeInfo"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            pairs = [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
            formatted = [f"{s[:-4]}/USDT" for s in pairs]
            return sorted(formatted)
    except:
        pass
    
    # Fallback default comprehensive list if API is restricted
    return [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", 
        "DOGE/USDT", "SUI/USDT", "PEPE/USDT", "AVAX/USDT", "LINK/USDT", "NEAR/USDT",
        "MATIC/USDT", "DOT/USDT", "SHIB/USDT", "UNI/USDT", "APT/USDT", "RENDER/USDT",
        "FET/USDT", "INJ/USDT", "AR/USDT", "OP/USDT", "ARB/USDT", "FTM/USDT", "ICP/USDT"
    ]

# 2. Resilient Chart Data Fetcher with multiple fallbacks
def fetch_chart_data(symbol, timeframe='1h', limit=100):
    clean_symbol = symbol.replace("/", "")
    
    # Try multiple Binance endpoints to avoid geo-blocking / IP blocks
    endpoints = [
        f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}",
        f"https://data-api.binance.vision/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}",
        f"https://api1.binance.com/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}"
    ]
    
    for url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'c_time', 'q_vol', 'n_trades', 'tb_base', 'tb_quote', 'ignore'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    for col in ['open', 'high', 'low', 'close', 'volume']: 
                        df[col] = df[col].astype(float)
                    return df
        except:
            continue
            
    return pd.DataFrame()

# --- UI LAYOUT ---
st.title("⚡ Binance Global Institutional Scanner")

all_pairs = get_all_usdt_pairs()
default_idx = all_pairs.index("BTC/USDT") if "BTC/USDT" in all_pairs else 0

selected_coin = st.sidebar.selectbox(
    "🔍 Type & Search Any Coin (USDT Pairs):", 
    all_pairs, 
    index=default_idx
)

timeframe = st.sidebar.selectbox("Timeframe:", ["5m", "15m", "1h", "4h", "1d"], index=2)

# --- DISPLAY SECTION ---
df = fetch_chart_data(selected_coin, timeframe)

if not df.empty:
    last_price = df['close'].iloc[-1]
    price_change = ((df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
    
    st.subheader(f"📊 Live Chart: {selected_coin} [{timeframe}] | Price: ${last_price:,.4f}")
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    
    st.metric(label=f"24h Trend / Change for {selected_coin}", value=f"${last_price:,.4f}", delta=f"{price_change:.2f}%")
else:
    st.warning(f"⚠️ Could not fetch live klines for {selected_coin} from Binance primary nodes. Please pick another coin or check network.")

