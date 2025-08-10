# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import requests
import uuid
import json

# --- Page Config ---
st.set_page_config(page_title="AI Financial Insights", page_icon="💹", layout="wide")

# --- Header ---
st.title("📊 Live Financial Trends & Investment Insights")
# --- Load Data ---
# @st.cache_data
# def load_data():
#     reports = pd.read_csv("data/reports_extracted.csv")
#     sentiment = pd.read_csv("data/sentiment.csv")
#     forecast = pd.read_csv("data/forecast.csv")
#     return reports, sentiment, forecast


reports_df, sentiment_df, forecast_df = load_data()

# --- Sidebar ---

st.sidebar.header("Financial Document analysis")
uploaded_file = st.sidebar.file_uploader("Upload your document", type=["pdf", "docx","txt"])

if uploaded_file:
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    webhook_url = (
        "https://techtwins.app.n8n.cloud/webhook/upload-file"  # change to your n8n URL
    )
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
    webhook_url = (
        "https://techtwins.app.n8n.cloud/webhook/ask"  # update with your actual URL
    )
    try:
        response = requests.post(webhook_url, json={"question": user_question,"sessionId": st.session_state.session_id})
        response.raise_for_status()
        answer = response.json().get("output", "No answer returned.")
    except Exception as e:
        answer = f"Error contacting server: {e}"

    # Add assistant answer to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # Clear input box
    # st.session_state.user_input = ""

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

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.title("Stock Prediction & Recommendation")

ticker = st.text_input("Enter ticker symbol", value="AAPL")
if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

if st.button("Get Prediction"):
    # 1. Fetch price series from Alpha Vantage
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize=compact&apikey=YOUR_API_KEY"
    )
    resp = requests.get(url)
    data = resp.json().get("Time Series (Daily)", {})

    # Convert to DataFrame
    df = pd.DataFrame.from_dict(data, orient="index").rename(
        columns={
            "1. open": "open",
            "2. high": "high",
            "3. low": "low",
            "4. close": "close",
            "5. volume": "volume",
        }
    )
    df.index = pd.to_datetime(df.index)
    df = df.astype(float)
    df = df.sort_index()

    # 2. Retrieve prediction from your backend (n8n webhook)
    payload = {"ticker": ticker, "sessionId": st.session_state.session_id}
    pred_res = requests.post(
        "https://techtwins.app.n8n.cloud/webhook/predict", json=payload
    )
    pred_res.raise_for_status()
    result = pred_res.json()
    raw = pred_res.json().get("output", "")

    st.write(raw)
    # Remove markdown fences
    cleaned = raw.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    data = json.loads(cleaned)
    pred = data["predicted_return"]
    rec = data["recommendation"]
    reason = data["reasoning"]

    # 3. Display forecast and the price chart
    st.subheader("Forecast & Recommendation")
    st.metric("Expected 7-Day Return", f"{pred}%")
    st.write(f"**Action:** {rec}")
    st.write(f"**Reasoning:** {reason}")

    fig = px.line(
        df,
        y="close",
        title=f"{ticker} - Recent Close Prices",
        labels={"close": "Close Price"},
    )
    st.plotly_chart(fig, use_container_width=True)
