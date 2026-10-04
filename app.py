import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib.request
from bs4 import BeautifulSoup
import re

# ページ基本設定
st.set_page_config(page_title="株式分析ダッシュボード", layout="wide")

# --- 日本株の会社名取得関数 ---
@st.cache_data(ttl=86400)
def get_company_name(symbol):
    """銘柄コードから会社名を取得する（日本株はYahoo!ファイナンスからスクレイピング）"""
    try:
        if symbol.endswith(".T"):
            code = symbol.replace(".T", "")
            url = f"https://finance.yahoo.co.jp/quote/{code}.T"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req).read()
            soup = BeautifulSoup(html, 'html.parser')
            
            # ページタイトルから会社名を抽出 (例: "トヨタ自動車(株)【7203】...")
            title = soup.find('title').text
            match = re.search(r'^(.*?)(?:\(|\【)', title)
            if match:
                return match.group(1).strip()
            return symbol
        else:
            # 米国株などは yfinance から取得
            ticker_info = yf.Ticker(symbol)
            return ticker_info.info.get('longName', symbol)
    except Exception:
        return symbol

# --- サイドバー設定 ---
st.sidebar.header("設定")
ticker_input = st.sidebar.text_input("銘柄コード（例: AAPL, 7203.T）", value="7203.T").strip().upper()
period = st.sidebar.selectbox("表示期間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

# データ取得処理（キャッシュ付き）
@st.cache_data(ttl=3600)
def load_data(symbol, p):
    df = yf.download(symbol, period=p)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# データ更新ボタン
if st.sidebar.button("🔄 最新データに更新"):
    st.cache_data.clear()
    st.rerun()

# 会社名の取得
company_name = get_company_name(ticker_input)

# タイトル表示
if company_name != ticker_input:
    st.title(f"📈 {company_name} ({ticker_input}) 分析ダッシュボード")
else:
    st.title(f"📈 {ticker_input} 分析ダッシュボード")

# データ読み込み
with st.spinner("データを取得中..."):
    data = load_data(ticker_input, period)

if data.empty:
    st.error("指定された銘柄のデータが見つかりませんでした。コードを確認してください。")
else:
    # --- テクニカル指標の計算 ---
    # 1. 移動平均線 (SMA)
    data["SMA20"] = data["Close"].rolling(window=20).mean()
    data["SMA50"] = data["Close"].rolling(window=50).mean()

    # 2. RSI (14日)
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # 3. MACD (12, 26, 9)
    exp1 = data["Close"].ewm(span=12, adjust=False).mean()
    exp2 = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = exp1 - exp2
    data["Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Hist"] = data["MACD"] - data["Signal"]

    # 基本指標表示
    latest_close = data["Close"].iloc[-1]
    prev_close = data["Close"].iloc[-2]
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("現在株価", f"{latest_close:,.2f}", f"{price_change:+,.2f} ({pct_change:+.2f}%)")
    col2.metric("期間最高値", f"{data['High'].max():,.2f}")
    col3.metric("期間最安値", f"{data['Low'].min():,.2f}")

    # --- 3段構成チャートの作成 ---
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=(f"株価チャート & 移動平均線", "RSI (14日)", "MACD (12, 26, 9)")
    )

    # 1段目: ローソク足 & SMA
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        name="株価"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], name="20日SMA", line=dict(color='orange', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA50'], name="50日SMA", line=dict(color='blue', width=1.5)), row=1, col=1)

    # 2段目: RSI
    fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='purple', width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # 3段目: MACD
    fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name="MACD", line=dict(color='blue', width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], name="シグナル", line=dict(color='orange', width=1.5)), row=3, col=1)
    fig.add_trace(go.Bar(x=data.index, y=data['MACD_Hist'], name="ヒストグラム", marker_color='gray'), row=3, col=1)

    fig.update_layout(
        height=750,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    fig.update_yaxes(range=[0, 100], row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # --- タブ分け（データ詳細 & 最新ニュース） ---
    tab1, tab2 = st.tabs(["📊 データ詳細", "📰 関連ニュース"])

    with tab1:
        st.dataframe(data[["Close", "SMA20", "SMA50", "RSI", "MACD"]].tail(10).sort_index(ascending=False), use_container_width=True)

    with tab2:
        st.subheader(f"最新のニュースフィード")
        try:
            ticker_obj = yf.Ticker(ticker_input)
            news_list = ticker_obj.news
            
            if news_list:
                for item in news_list[:5]:
                    # yfinanceのニュースデータ形式に対応
                    title = item.get('title') or item.get('content', {}).get('title', 'No Title')
                    link = item.get('link') or item.get('content', {}).get('canonicalUrl', {}).get('url', '#')
                    publisher = item.get('publisher') or item.get('content', {}).get('provider', {}).get('displayName', 'Unknown')
                    
                    st.markdown(f"**[{title}]({link})**")
                    st.caption(f"配信元: {publisher}")
                    st.divider()
            else:
                st.info("現在表示できるニュースはありません。")
        except Exception as e:
            st.warning("ニュースの取得中にエラーが発生しました。")
