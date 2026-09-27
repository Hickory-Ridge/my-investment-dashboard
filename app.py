import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="投資分析ダッシュボード", layout="wide")

st.title("📈 投資情報分析ダッシュボード")

# キャッシュ付きのデータ取得関数
@st.cache_data(ttl=300)
def load_stock_data(ticker_symbol, period):
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period)
    info = ticker.info
    return df, info

# サイドバー設定
st.sidebar.header("検索・分析条件")
ticker_symbol = st.sidebar.text_input("銘柄コード (例: AAPL, 7203.T)", value="AAPL")
period = st.sidebar.selectbox("分析期間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

# 最新データへ更新ボタン
if st.sidebar.button("🔄 最新データに更新"):
    st.cache_data.clear()
    st.rerun()

# データ取得
with st.spinner("最新データを取得中..."):
    df, info = load_stock_data(ticker_symbol, period)

if not df.empty:
    col1, col2, col3, col4 = st.columns(4)
    latest_price = df["Close"].iloc[-1]
    prev_price = df["Close"].iloc[-2]
    change = latest_price - prev_price

    col1.metric("現在値", f"${latest_price:.2f}", f"{change:.2f}")
    col2.metric("PER", f"{info.get('trailingPE', 'N/A')}")
    col3.metric("PBR", f"{info.get('priceToBook', 'N/A')}")
    col4.metric("配当利回り", f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "N/A")

    # テクニカルチャート
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="株価"))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], mode='lines', name='SMA 20'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], mode='lines', name='SMA 50'))
    fig.update_layout(title=f"{ticker_symbol} 株価チャート", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("銘柄コードを確認してください。")
