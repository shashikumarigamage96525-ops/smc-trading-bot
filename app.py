# 5. Professional Pattern Engine (Trend-Aware)
def detect_dominant_pattern(df):
    if df.empty or len(df) < 100:
        return [], [], None
    
    # Trend Indicator (Price vs EMA 200)
    current_price = df['close'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    is_bullish_trend = current_price > ema_200
    is_bearish_trend = current_price < ema_200
    
    highs = df['high'].values
    lows = df['low'].values
    times = df['timestamp'].values
    
    # 1. Identify Trend First
    trend_desc = "Strong Bearish" if is_bearish_trend else ("Strong Bullish" if is_bullish_trend else "Consolidation")
    
    dominant_pattern = None
    
    # 2. Logic: Double Bottom (Only valid if trend is Bullish or Neutral)
    if is_bullish_trend:
        recent_lows = lows[-40:]
        min_l = min(recent_lows)
        # Check for two distinct troughs with distance
        troughs = [i for i, l in enumerate(recent_lows) if l < min_l * 1.01]
        if len(troughs) >= 2 and (troughs[-1] - troughs[0]) > 15:
            dominant_pattern = {
                'name': 'Double Bottom (Bullish)',
                'level': min_l,
                'bias': 'Bullish',
                'desc': 'Bullish Trend confirmed. Pattern valid.'
            }
    
    # 3. Logic: Double Top (Only valid if trend is Bearish or Neutral)
    if is_bearish_trend:
        recent_highs = highs[-40:]
        max_h = max(recent_highs)
        peaks = [i for i, h in enumerate(recent_highs) if h > max_h * 0.99]
        if len(peaks) >= 2 and (peaks[-1] - peaks[0]) > 15:
            dominant_pattern = {
                'name': 'Double Top (Bearish)',
                'level': max_h,
                'bias': 'Bearish',
                'desc': 'Bearish Trend confirmed. Pattern valid.'
            }
            
    return trend_desc, dominant_pattern

# --- UI කොටසේ අලුත් එකතු කිරීම ---
trend_desc, pattern = detect_dominant_pattern(df)

st.markdown(f"### 📈 Market Analysis: {trend_desc} Trend")

if pattern and pattern['bias'] == 'Bullish' and trend_desc != "Strong Bearish":
    st.success(f"✅ Valid Pattern: {pattern['name']} detected at ${pattern['level']:.4f}")
elif pattern and pattern['bias'] == 'Bearish' and trend_desc != "Strong Bullish":
    st.error(f"⚠️ Valid Pattern: {pattern['name']} detected at ${pattern['level']:.4f}")
else:
    st.info("ℹ️ Market is in {trend_desc} state. No high-probability patterns confirmed.")
