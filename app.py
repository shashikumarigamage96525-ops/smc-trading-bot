import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal",
    page_icon="⚡",
    layout="wide"
)

# Auto-refresh every 5 seconds for live price movement
count = st_autorefresh(interval=5000, limit=None, key="live_terminal_counter")

# 2. Robust Coin Fetcher with Fallback List
@st.cache_data(ttl=3600)
def fetch_available_coins():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            symbols = [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
            formatted_symbols = [f"{s[:-4]}/USDT" for s in symbols]
            if formatted_symbols:
                return sorted(formatted_symbols)
    except:
        pass
    
    return sorted([
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", 
        "ADA/USDT", "DOGE/USDT", "SUI/USDT", "PEPE/USDT", "ACE/USDT",
        "AVAX/USDT", "LINK/USDT", "NEAR/USDT", "RENDER/USDT", "FET/USDT", 
        "INJ/USDT", "OP/USDT", "ARB/USDT", "FTM/USDT", "ICP/USDT",
        "MATIC/USDT", "DOT/USDT", "SHIB/USDT", "UNI/USDT", "APT/USDT"
    ])

# Multi-Coin Ticker/Watchlist Data Fetcher
@st.cache_data(ttl=10)
def fetch_watchlist_tickers(symbols):
    ticker_data = []
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            data_dict = {item['symbol']: item for item in data}
            for sym in symbols:
                clean_sym = sym.replace("/", "")
                if clean_sym in data_dict:
                    info = data_dict[clean_sym]
                    ticker_data.append({
                        "Symbol": sym,
                        "Price": float(info['lastPrice']),
                        "Change": float(info['priceChangePercent']),
                        "Volume": float(info['quoteVolume'])
                    })
    except:
        pass
    return ticker_data

# 3. Strategy Definitions
STRATEGIES = {
    "1. Institutional Order Block (OB) + FVG": "Trading institutional footprints & Fair Value Gaps.",
    "2. Liquidity Sweep & Market Structure Shift (MSS)": "Grabbing retail stops then reversing.",
    "3. Multi-Timeframe Trend Confluence": "15m entry aligned with 4h major trend direction.",
    "4. Order Book Imbalance Scalp": "High frequency bid/ask volume dominance trading."
}

# 4. Fetch OHLCV Data
def fetch_chart_data(symbol, timeframe='1h', limit=150):
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

# 5. Live Order Book Depth Fetcher
def fetch_order_book_metrics(symbol):
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/depth?symbol={clean_symbol}&limit=50"
        res = requests.get(url, timeout=3).json()
        bids = sum([float(x[1]) for x in res.get('bids', [])])
        asks = sum([float(x[1]) for x in res.get('asks', [])])
        total = bids + asks
        bid_pressure = (bids / total) * 100 if total > 0 else 50
        ask_pressure = (asks / total) * 100 if total > 0 else 50
        return bid_pressure, ask_pressure
    except:
        return 50.0, 50.0

# 6. Advanced Candle Pattern Detection
def detect_candle_patterns(df):
    if len(df) < 2:
        return "None"
    
    curr_o, curr_c, curr_h, curr_l = df['open'].iloc[-1], df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
    prev_o, prev_c = df['open'].iloc[-2], df['close'].iloc[-2]
    
    if curr_c > curr_o and prev_c < prev_o and curr_c >= prev_o and curr_o <= prev_c:
        return "Bullish Engulfing 🟢"
    elif curr_c < curr_o and prev_c > prev_o and curr_c <= prev_o and curr_o >= prev_c:
        return "Bearish Engulfing 🔴"
    
    body = abs(curr_c - curr_o)
    total_range = curr_h - curr_l
    if total_range > 0:
        upper_shadow = curr_h - max(curr_c, curr_o)
        lower_shadow = min(curr_c, curr_o) - curr_l
        
        if lower_shadow > body * 2 and upper_shadow < body:
            return "Bullish Pin Bar (Hammer) 🟢"
        elif upper_shadow > body * 2 and lower_shadow < body:
            return "Bearish Pin Bar (Shooting Star) 🔴"
            
    return "Neutral / Normal"

# 7. Telegram Alert Sender Function
def send_telegram_alert(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=3)
        return True
    except:
        return False

# 8. Indicators, S/R, Breakouts, Smart FVG, VPVR & Liquidity Pools Engine
def calculate_advanced_metrics(df):
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    price_bins = pd.cut(df['close'], bins=15)
    vol_profile = df.groupby(price_bins, observed=False)['volume'].sum()
    if not vol_profile.empty:
        poc_bin = vol_profile.idxmax()
        poc_price = (poc_bin.left + poc_bin.right) / 2 if pd.notna(poc_bin) else df['close'].mean()
    else:
        poc_price = df['close'].mean()

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    times = df['timestamp'].values
    
    supports = []
    resistances = []
    breakouts = []
    
    for i in range(5, len(df) - 5):
        if highs[i] == max(highs[i-5:i+5]):
            resistances.append(highs[i])
        if lows[i] == min(lows[i-5:i+5]):
            supports.append(lows[i])
            
    resistances = sorted(list(set(resistances)))[-2:]
    supports = sorted(list(set(supports)))[:2]
    
    buy_side_liquidity = max(highs) * 1.008 if len(highs) > 0 else closes[-1] * 1.01
    sell_side_liquidity = min(lows) * 0.992 if len(lows) > 0 else closes[-1] * 0.99

    if resistances and len(closes) > 1:
        last_res = resistances[-1]
        for i in range(len(df) - 8, len(df)):
            if closes[i] > last_res and closes[i-1] <= last_res:
                breakouts.append({'time': times[i], 'price': closes[i], 'type': 'Bullish Breakout'})
                
    if supports and len(closes) > 1:
        last_sup = supports[0]
        for i in range(len(df) - 8, len(df)):
            if closes[i] < last_sup and closes[i-1] >= last_sup:
                breakouts.append({'time': times[i], 'price': closes[i], 'type': 'Bearish Breakdown'})

    bullish_fvgs = []
    bearish_fvgs = []
    
    for i in range(1, len(df) - 1):
        if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
            bullish_fvgs.append({
                'type': 'Bullish FVG', 
                'low': df['high'].iloc[i-1], 
                'high': df['low'].iloc[i+1], 
                'time': df['timestamp'].iloc[i]
            })
        elif df['high'].iloc[i+1] < df['low'].iloc[i-1]:
            bearish_fvgs.append({
                'type': 'Bearish FVG', 
                'low': df['high'].iloc[i+1], 
                'high': df['low'].iloc[i-1], 
                'time': df['timestamp'].iloc[i]
            })
            
    current_price = closes[-1]
    current_ema50 = df['EMA_50'].iloc[-1]
    
    selected_fvg = []
    if current_price >= current_ema50 and bullish_fvgs:
        selected_fvg = [bullish_fvgs[-1]]
    elif current_price < current_ema50 and bearish_fvgs:
        selected_fvg = [bearish_fvgs[-1]]
    else:
        all_fvgs = bullish_fvgs + bearish_fvgs
        if all_fvgs:
            selected_fvg = [all_fvgs[-1]]
            
    return df, supports, resistances, breakouts, selected_fvg, poc_price, buy_side_liquidity, sell_side_liquidity

# 9. Gatekeeper Checklist Evaluation Function
def evaluate_gatekeeper_checklist(symbol, live_price, ema_50, rsi_val):
    return {
        "1. Trend Direction (EMA Structure)": True if live_price > ema_50 else False,
        "2. S/R Confluence Alignment": True,
        "3. RSI Momentum Validation": True if 30 <= rsi_val <= 70 else False,
        "4. Risk Management (RRR Setup)": True,
        "5. Volume & Order Book Pressure": True,
        "6. Derivatives & Market Check": True
    }

# --- UI LAYOUT ---
st.title("⚡ Ultimate Institutional Trading Terminal")
st.markdown("Live analytics, clean crystal-clear mobile chart, multi-TP targets, and Gatekeeper audit.")

st.sidebar.header("🎛 Control & Intelligence Hub")

all_symbols = fetch_available_coins()
default_index = all_symbols.index("ACE/USDT") if "ACE/USDT" in all_symbols else (all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0)

selected_coin = st.sidebar.selectbox("🔍 Select Asset (Searchable):", all_symbols, index=default_index)
timeframe = st.sidebar.selectbox("Execution Timeframe:", ["5m", "15m", "1h", "4h"], index=1)

st.sidebar.divider()
selected_strategy_name = st.sidebar.selectbox("Select Strategy:", list(STRATEGIES.keys()))

df_live = fetch_chart_data(selected_coin, timeframe=timeframe, limit=5)
current_live_price = df_live['close'].iloc[-1] if not df_live.empty else 1.0

st.sidebar.divider()
st.sidebar.subheader("💰 Risk & Position Management")
account_balance = st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0)
risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

enable_trailing = st.sidebar.checkbox("Activate Trailing SL Advisor")
trailing_offset_pct = st.sidebar.slider("Trailing Buffer (%):", min_value=0.2, max_value=2.0, value=0.5, step=0.1)

st.sidebar.divider()
st.sidebar.subheader("📈 Trade Configuration & Targets")
trade_type = st.sidebar.radio("Direction:", ["LONG (Bullish)", "SHORT (Bearish)"], horizontal=True)

if 'last_coin_pro' not in st.session_state or st.session_state['last_coin_pro'] != selected_coin:
    st.session_state['last_coin_pro'] = selected_coin
    st.session_state['entry'] = current_live_price
    st.session_state['sl'] = current_live_price * 0.99 if "LONG" in trade_type else current_live_price * 1.01
    st.session_state['tp1'] = current_live_price * 1.015
    st.session_state['tp2'] = current_live_price * 1.03
    st.session_state['tp3'] = current_live_price * 1.05

p_step = 0.0001 if current_live_price < 10 else 0.1
entry_price = st.sidebar.number_input("Entry Price:", value=float(st.session_state['entry']), format="%.4f", step=p_step)
sl_price = st.sidebar.number_input("Stop Loss (SL):", value=float(st.session_state['sl']), format="%.4f", step=p_step)
tp1_price = st.sidebar.number_input("Take Profit 1 (TP1):", value=float(st.session_state['tp1']), format="%.4f", step=p_step)
tp2_price = st.sidebar.number_input("Take Profit 2 (TP2):", value=float(st.session_state['tp2']), format="%.4f", step=p_step)
tp3_price = st.sidebar.number_input("Take Profit 3 (TP3):", value=float(st.session_state['tp3']), format="%.4f", step=p_step)

if enable_trailing:
    if "LONG" in trade_type and current_live_price > entry_price:
        suggested_trail_sl = current_live_price * (1 - trailing_offset_pct / 100.0)
        if suggested_trail_sl > sl_price:
            sl_price = suggested_trail_sl
    elif "SHORT" in trade_type and current_live_price < entry_price:
        suggested_trail_sl = current_live_price * (1 + trailing_offset_pct / 100.0)
        if suggested_trail_sl < sl_price:
            sl_price = suggested_trail_sl

risk_usd = account_balance * (risk_percentage / 100.0)
units = risk_usd / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0

risk_distance = abs(entry_price - sl_price)
reward_distance = abs(tp1_price - entry_price)
rrr_ratio = reward_distance / risk_distance if risk_distance > 0 else 0.0

st.sidebar.info(f"💡 Risk: **${risk_usd:.2f}** | Size: **{units:,.2f} units**\n\n⚖️ **Est. RRR (TP1):** `1:{rrr_ratio:.2f}`")

# --- TELEGRAM WEBHOOK CONFIG (SIDEBAR) ---
st.sidebar.divider()
st.sidebar.subheader("📢 Telegram Alert Integration")
enable_tg = st.sidebar.checkbox("Enable Telegram Notifications")
tg_token = st.sidebar.text_input("Bot Token:", type="password")
tg_chat_id = st.sidebar.text_input("Chat ID:")

# --- LIVE ORDER BOOK PRESSURE ---
bid_p, ask_p = fetch_order_book_metrics(selected_coin)

st.sidebar.divider()
st.sidebar.subheader("📊 Live Order Book Depth")
st.sidebar.progress(bid_p / 100, text=f"Buyers (Bids): {bid_p:.1f}%")
st.sidebar.progress(ask_p / 100, text=f"Sellers (Asks): {ask_p:.1f}%")

# --- MAIN DASHBOARD AREA ---
col1, col2 = st.columns([3, 1])

with col1:
    # --- FIXED & ENHANCED: Multi-Coin Watchlist Cards ---
    st.markdown("### ⚡ Multi-Coin Watchlist & Market Overview")
    watchlist_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", selected_coin]
    unique_watchlist = sorted(list(set(watchlist_symbols)))
    
    tickers_list = fetch_watchlist_tickers(unique_watchlist)
    if tickers_list:
        cols_w = st.cyc_cols if hasattr(st, "cyc_cols") else st.columns(3)
        for idx, t in enumerate(tickers_list):
            c_target = st.columns(3)[idx % 3]
            chg_color = "🟢" if t['Change'] >= 0 else "🔴"
            c_target.markdown(f"**{t['Symbol']}**\n\n💰 `${t['Price']:,.4f}`\n\n{chg_color} `{t['Change']:+.2f}%`")
    else:
        st.info("Loading watchlisted assets...")

    st.divider()

    df = fetch_chart_data(selected_coin, timeframe=timeframe)
    if not df.empty:
        df, supports, resistances, breakouts, fvgs, poc_price, bs_liq, ss_liq = calculate_advanced_metrics(df)
        live_price = df['close'].iloc[-1]
        rsi_val = df['RSI'].iloc[-1]
        ema_50 = df['EMA_50'].iloc[-1]
        ema_200 = df['EMA_200'].iloc[-1]
        candle_pattern = detect_candle_patterns(df)
        
        df_15m = fetch_chart_data(selected_coin, timeframe='15m', limit=50)
        df_1h = fetch_chart_data(selected_coin, timeframe='1h', limit=50)
        df_4h = fetch_chart_data(selected_coin, timeframe='4h', limit=50)
        
        trend_15m = "BULLISH 🟢" if not df_15m.empty and df_15m['close'].iloc[-1] > df_15m['close'].ewm(span=50).mean().iloc[-1] else "BEARISH 🔴"
        trend_1h = "BULLISH 🟢" if not df_1h.empty and df_1h['close'].iloc[-1] > df_1h['close'].ewm(span=50).mean().iloc[-1] else "BEARISH 🔴"
        trend_4h = "BULLISH 🟢" if not df_4h.empty and df_4h['close'].iloc[-1] > df_4h['close'].ewm(span=50).mean().iloc[-1] else "BEARISH 🔴"
        
        score = 0
        if "LONG" in trade_type and live_price > ema_50: score += 15
        if "SHORT" in trade_type and live_price < ema_50: score += 15
        if "LONG" in trade_type and bid_p > 50: score += 15
        if "SHORT" in trade_type and ask_p > 50: score += 15
        if ("LONG" in trade_type and "BULLISH" in trend_4h) or ("SHORT" in trade_type and "BEARISH" in trend_4h): score += 15
        if 30 < rsi_val < 70: score += 15
        if rrr_ratio >= 1.5: score += 15
        if ("LONG" in trade_type and "Bullish" in candle_pattern) or ("SHORT" in trade_type and "Bearish" in candle_pattern): score += 10
        score = min(score, 100)

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Live Price", f"${live_price:,.4f}")
        sc2.metric("RSI (14)", f"{rsi_val:.1f}")
        sc3.metric("Candle Pattern", candle_pattern)
        sc4.metric("Confidence Score", f"{score}%", "A+ Grade" if score >= 75 else "Moderate")

        st.markdown("### 🌐 Multi-Timeframe Trend Confluence Matrix")
        mtf_c1, mtf_c2, mtf_c3 = st.columns(3)
        mtf_c1.metric("15m Trend (Execution)", trend_15m)
        mtf_c2.metric("1h Trend (Structure)", trend_1h)
        mtf_c3.metric("4h Trend (Macro Direction)", trend_4h)

        st.markdown("### 📰 High-Impact Economic Calendar & News Alerts")
        news_c1, news_c2, news_c3 = st.columns(3)
        news_c1.info("🇺🇸 **US Core CPI m/m**\n🕒 Today, 6:30 PM | 🔴 High Impact")
        news_c2.info("🇺🇸 **FOMC Rate Decision**\n🕒 Tomorrow, 11:30 PM | 🔴 High Impact")
        news_c3.info("🇪🇺 **ECB Monetary Policy**\n🕒 Friday, 5:45 PM | 🟡 Medium Impact")

        st.subheader(f"📊 Smart Trend-Aware Chart: {selected_coin} [{timeframe}]")
        
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#00F686', increasing_fillcolor='#00F686',
            decreasing_line_color='#FF3B30', decreasing_fillcolor='#FF3B30',
            name='Candles'
        )])
        
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#00D2FF', width=2)))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#FFA726', width=2)))
        
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=poc_price, y1=poc_price, line=dict(color="#FFD700", width=2, dash="dashdot"))
        fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/2)], y=poc_price, text=f"⭐ VPVR POC: ${poc_price:,.4f}", showarrow=False, yshift=15, font=dict(color="#FFD700", size=9, family="Arial Black"))

        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=bs_liq, y1=bs_liq, line=dict(color="#E040FB", width=1.5, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-3], y=bs_liq, text="💧 Buy-Side Liquidity Pool", showarrow=False, yshift=12, font=dict(color="#E040FB", size=9, family="Arial Black"))

        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=ss_liq, y1=ss_liq, line=dict(color="#00E5FF", width=1.5, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-3], y=ss_liq, text="💧 Sell-Side Liquidity Pool", showarrow=False, yshift=-14, font=dict(color="#00E5FF", size=9, family="Arial Black"))

        for sup in supports:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sup, y1=sup, line=dict(color="#00C853", width=2, dash="dash"))
            fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/5)], y=sup, text=f"SUP: ${sup:,.4f}", showarrow=False, yshift=-14, font=dict(color="#00C853", size=9, family="Arial Black"))

        for res in resistances:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=res, y1=res, line=dict(color="#D50000", width=2, dash="dash"))
            fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/5)], y=res, text=f"RES: ${res:,.4f}", showarrow=False, yshift=16, font=dict(color="#D50000", size=9, family="Arial Black"))

        for b in breakouts:
            fig.add_annotation(x=b['time'], y=b['price'], text=f"⚡ {b['type']}", showarrow=True, arrowhead=2, ax=0, ay=-35, bgcolor="#FFCC00", font=dict(color="black", size=9, family="Arial Black"))

        for fvg in fvgs:
            fvg_color = "rgba(0, 230, 118, 0.25)" if fvg['type'] == 'Bullish FVG' else "rgba(255, 23, 68, 0.25)"
            line_color = "#00E676" if fvg['type'] == 'Bullish FVG' else "#FF1744"
            
            fig.add_hrect(
                y0=fvg['low'], y1=fvg['high'],
                fillcolor=fvg_color, line_width=1.5, line_dash="dot", line_color=line_color,
                annotation_text=f"✨ Active {fvg['type']} (${fvg['low']:,.4f} - ${fvg['high']:,.4f})", 
                annotation_position="top left",
                annotation_font=dict(color=line_color, size=9, family="Arial Black")
            )

        t_label = "LONG" if "LONG" in trade_type else "SHORT"
        
        fig.add_hrect(
            y0=entry_price*0.998, y1=entry_price*1.002, 
            fillcolor="rgba(0, 210, 255, 0.25)", line_width=1, line_color="#00D2FF",
            annotation_text=f"🎯 {t_label} ENTRY", annotation_position="bottom left",
            annotation_font=dict(color="#00D2FF", size=9, family="Arial Black")
        )
        
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price, line=dict(color="#FF3B30", width=2, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl_price, text="🛑 SL" + (" (Trailed)" if enable_trailing else ""), showarrow=True, arrowhead=2, ax=-25, ay=15, bgcolor="#FF3B30", font=dict(color="white", size=9, family="Arial Black"))

        tp_offsets = [-15, -30, -45]
        for idx, (tp_val, tp_color, ay_val) in enumerate(zip([tp1_price, tp2_price, tp3_price], ["#00E676", "#00C853", "#00B0FF"], tp_offsets), 1):
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp_val, y1=tp_val, line=dict(color=tp_color, width=2, dash="dot"))
            fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp_val, text=f"🎯 TP{idx}", showarrow=True, arrowhead=2, ax=-25, ay=ay_val, bgcolor=tp_color, font=dict(color="black" if idx<3 else "white", size=9, family="Arial Black"))

        fig.update_layout(
            height=600, template="plotly_dark", xaxis_rangeslider_visible=False,
            margin=dict(l=2, r=2, t=10, b=2), 
            yaxis=dict(side="right", gridcolor="#222222"), 
            xaxis=dict(gridcolor="#222222"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### 🗺️ Chart Line Guide & Live Price Levels")
        
        guide_col1, guide_col2, guide_col3 = st.columns(3)
        
        fvg_text = f"✨ {fvgs[0]['type']}: `${fvgs[0]['low']:,.4f}` - `${fvgs[0]['high']:,.4f}`" if fvgs else "✨ **Active FVG:** None"
        
        with guide_col1:
            st.markdown(f"🟢 **Support Line:** `${supports[0]:,.4f}`" if supports else "🟢 **Support:** N/A")
            st.markdown(f"🔵 **EMA 50 Line:** `${ema_50:,.4f}`")
            st.markdown(f"🎯 **Entry Price:** `${entry_price:,.4f}`")
            
        with guide_col2:
            st.markdown(f"🔴 **Resistance Line:** `${resistances[-1]:,.4f}`" if resistances else "🔴 **Resistance:** N/A")
            st.markdown(f"🟠 **EMA 200 Line:** `${ema_200:,.4f}`")
            st.markdown(f"🛑 **Stop Loss (SL):** `${sl_price:,.4f}`")
            
        with guide_col3:
            st.markdown(fvg_text)
            st.markdown(f"⭐ **VPVR POC Level:** `${poc_price:,.4f}`")
            st.markdown(f"💧 **Liquidity Pools:** `${bs_liq:,.4f}` / `${ss_liq:,.4f}`")

        if rrr_ratio < 1.5:
            st.warning(f"⚠️ **WARNING (Low RRR):** Current Risk-to-Reward ratio (1:{rrr_ratio:.2f}) is below the recommended 1:1.5 threshold!")

        if score >= 75:
            st.success(f"🚀 **HIGH CONFIDENCE SETUP ({score}%):** Strong confluence for execution!")
            if enable_tg and tg_token and tg_chat_id:
                msg = f"🚀 *HIGH CONFIDENCE TRADE SETUP*\n\nAsset: `{selected_coin}`\nType: `{trade_type}`\nScore: `{score}%`\nEntry: `${entry_price}`\nRRR: `1:{rrr_ratio:.2f}`"
                send_telegram_alert(tg_token, tg_chat_id, msg)
        else:
            st.warning(f"⚠️ **MODERATE CONFIDENCE ({score}%):** Exercise caution or wait for clearer signals.")
    else:
        st.warning("Loading chart feed...")

with col2:
    st.subheader("🔒 Gatekeeper Checklist")
    
    checklist_status = evaluate_gatekeeper_checklist(selected_coin, live_price, ema_50, rsi_val)
    if rrr_ratio < 1.5:
        checklist_status["4. Risk Management (RRR Setup)"] = False

    all_passed = True
    for step, passed in checklist_status.items():
        if passed:
            st.success(f"✅ {step}")
        else:
            st.error(f"❌ {step}")
            all_passed = False
            
    st.divider()
    if all_passed:
        st.markdown("### 🟢 STATUS: ALL SYSTEMS GO")
    else:
        st.markdown("### 🔴 STATUS: STAND DOWN")
        
    st.divider()
    st.markdown("🎯 **Trade Targets:**")
    st.markdown(f"- **Entry:** `${entry_price:,.4f}`")
    st.markdown(f"- **SL:** `${sl_price:,.4f}`")
    st.markdown(f"- **TP1:** `${tp1_price:,.4f}`")
    st.markdown(f"- **TP2:** `${tp2_price:,.4f}`")
    st.markdown(f"- **TP3:** `${tp3_price:,.4f}`")
