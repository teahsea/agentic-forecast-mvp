# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import requests
import uuid

# --- Page Config ---
st.set_page_config(page_title="AI Financial Insights", page_icon="💹", layout="wide")

# --- Header ---
st.title("📊 Live Financial Trends & Investment Insights")
# --- Load Data ---
@st.cache_data
def load_data():
    reports = pd.read_csv("data/reports_extracted.csv")
    sentiment = pd.read_csv("data/sentiment.csv")
    forecast = pd.read_csv("data/forecast.csv")
    return reports, sentiment, forecast


reports_df, sentiment_df, forecast_df = load_data()

# --- Sidebar ---

st.sidebar.header("Financial Document analysis")
uploaded_file = st.sidebar.file_uploader("Upload your document", type=["pdf", "docx","txt"])

if uploaded_file:
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    webhook_url = "https://techtwins.app.n8n.cloud/webhook-test/upload-file"  # change to your n8n URL
    res = requests.post(webhook_url, files=files)
    st.json(res.json())

st.sidebar.markdown("---")

# Initialize chat history in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.sidebar.header("Financial Q&A Chatbot")

user_question = st.sidebar.text_input("Ask a financial question", key="user_input")

if user_question:
    # Add user question to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    # Send question to n8n webhook
    webhook_url = "https://techtwins.app.n8n.cloud/webhook-test/ask"  # update with your actual URL
    try:
        response = requests.post(webhook_url, json={"question": user_question,"sessionId": st.session_state.session_id})
        response.raise_for_status()
        answer = response.json().get("output", "No answer returned.")
    except Exception as e:
        answer = f"Error contacting server: {e}"

    # Add assistant answer to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # Clear input box
    #st.session_state.user_input = ""

# Display chat bubbles
st.sidebar.header("💬 Conversation History")

for chat in st.session_state.chat_history:
    if chat["role"] == "user":
        st.markdown(
            f"""
        <div style='text-align: right; background-color: #DCF8C6; padding: 8px; border-radius: 10px; margin: 5px 0; max-width: 70%; margin-left: auto;'>
            {chat['content']}
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
        <div style='text-align: left; background-color: #F1F0F0; padding: 8px; border-radius: 10px; margin: 5px 0; max-width: 70%; margin-right: auto;'>
            {chat['content']}
        </div>
        """,
            unsafe_allow_html=True,
        )

ticker_list = (
    reports_df["ticker"].unique().tolist() if not reports_df.empty else ["AAPL", "MSFT"]
)
selected_ticker = st.selectbox("Select Company/Ticker", ticker_list)

# --- Filter Data ---
ticker_reports = reports_df[reports_df["ticker"] == selected_ticker]
ticker_sentiment = sentiment_df[sentiment_df["ticker"] == selected_ticker]
ticker_forecast = forecast_df[forecast_df["ticker"] == selected_ticker]

# --- KPI Row ---
col1, col2, col3 = st.columns(3)
latest_price = ticker_forecast["actual"].iloc[-1] if not ticker_forecast.empty else None
recommendation = "Buy"  # Placeholder logic for now
sentiment_score = (
    ticker_sentiment["sentiment_score"].mean() if not ticker_sentiment.empty else 0
)

col1.metric("Latest Price", f"${latest_price:.2f}" if latest_price else "N/A")
col2.metric("Sentiment", f"{sentiment_score:.2f}")
col3.metric("Recommendation", recommendation)

st.markdown("---")

# --- Forecast Chart ---
if not ticker_forecast.empty:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ticker_forecast["date"],
            y=ticker_forecast["actual"],
            mode="lines",
            name="Actual Price",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ticker_forecast["date"],
            y=ticker_forecast["forecast"],
            mode="lines",
            name="Forecast Price",
        )
    )
    if (
        "yhat_lower" in ticker_forecast.columns
        and "yhat_upper" in ticker_forecast.columns
    ):
        fig.add_trace(
            go.Scatter(
                x=list(ticker_forecast["date"]) + list(ticker_forecast["date"][::-1]),
                y=list(ticker_forecast["yhat_upper"])
                + list(ticker_forecast["yhat_lower"][::-1]),
                fill="toself",
                fillcolor="rgba(0,100,80,0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                name="Confidence Interval",
            )
        )
    fig.update_layout(title="Price Forecast", xaxis_title="Date", yaxis_title="Price")
    st.plotly_chart(fig, use_container_width=True)

# --- Sentiment Table ---
st.subheader("📈 Sentiment Over Time")
if not ticker_sentiment.empty:
    st.line_chart(ticker_sentiment.set_index("date")["sentiment_score"])
else:
    st.info("No sentiment data available.")

# --- Reports Table ---
st.subheader("📄 Latest Financial Reports")
if not ticker_reports.empty:
    st.dataframe(ticker_reports)
else:
    st.info("No reports available.")

#
# --- Explain Recommendation ---
with st.expander("Why this recommendation?"):
    st.write("Placeholder explanation — replace with real decision rules output.")
    st.write("Example: Forecast ↑ 5%, sentiment +0.2 → BUY signal.")

# --- Footer ---
st.markdown("---")
st.caption("Built in 16h Hackathon with n8n + Streamlit 🚀")
