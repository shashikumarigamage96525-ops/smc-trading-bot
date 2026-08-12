import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Pro Trading", layout="wide")

# yfinance භාවිතා කරමින් දත්ත ලබාගැනීම
@st.cache_data(ttl=300)
def fetch_data(symbol):
    try:
        # Binance symbol format එක yfinance වලට හරවා ගැනීම (ADA/USDT -> ADA-USD)
        ticker = symbol.replace("/", "-")
        df = yf.download(ticker, period="5d", interval="1h")
        if df.empty:
            return None
        
        # දත්ත නිවැරදි කිරීම
        df.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        return df
    except:
        return None

symbol = st.sidebar.selectbox("Select Coin", ["BTC-USD", "ETH-USD", "ADA-USD"])
df = fetch_data(symbol)

if df is not None:
    st.write(f"### Chart for {symbol}")
    
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], name='EMA 200', line=dict(color='orange')))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("දත්ත ලැබීම ප්‍රමාදයි. කරුණාකර 'Manage App' වෙත ගොස් 'Reboot' කරන්න.")
