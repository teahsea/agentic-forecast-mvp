import os
import time
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Agentic Finance — Minimal MVP", page_icon="📈", layout="wide")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.title("📈 Agentic Finance — Minimal MVP")
st.caption("Upload a doc (optional), choose a task, and see a single-stock forecast suggestion for the demo.")

# ---------- Sidebar: super minimal inputs ----------
with st.sidebar:
    st.header("Inputs")
    uploaded = st.file_uploader("Upload document (optional, .pdf/.txt)", type=["pdf","txt"], accept_multiple_files=False)
    prompt = st.text_area("Prompt (optional)", value="Summarize key risks and opportunities.")
    task_label = st.radio("Task", ["Document Q&A", "Forecast+Strategy"], index=1, horizontal=True)
    task = {"Document Q&A":"qa","Forecast+Strategy":"strategy"}[task_label]
    symbol = st.text_input("Stock symbol", value="INFY")
    horizon = st.number_input("Horizon (days)", min_value=1, max_value=30, value=5, step=1)
    start_btn = st.button("Run", type="primary", use_container_width=True)

# Extract text lightly (no PDF parsing to keep it minimal)
doc_name, doc_text = None, None
if uploaded is not None:
    doc_name = uploaded.name
    try:
        if uploaded.type == "text/plain":
            doc_text = uploaded.read().decode("utf-8", errors="ignore")
        else:
            # Keep minimal: don't parse PDFs in this demo
            doc_text = None
    except Exception:
        doc_text = None

# ---------- Trigger run ----------
if start_btn:
    payload = {
        "user_id": "demo-user",
        "symbols": [symbol.strip()] if symbol.strip() else [],
        "horizon_days": int(horizon),
        "prompt": (prompt or None),
        "doc_name": doc_name,
        "doc_text": doc_text,
        "task": task,
    }
    try:
        r = requests.post(f"{API_BASE}/runs", json=payload, timeout=30)
        r.raise_for_status()
        st.session_state["run_id"] = r.json()["run_id"]
        st.success("Run started.")
    except Exception as e:
        st.error(f"Could not start run: {e}")

run_id = st.session_state.get("run_id")

# ---------- Main area ----------
if not run_id:
    st.info("Select a task and click **Run**.")
else:
    with st.spinner("Running…"):
        status_placeholder = st.empty()
        bar = st.progress(0)
        for _ in range(120):
            try:
                s = requests.get(f"{API_BASE}/runs/{run_id}", timeout=10).json()
                prog = float(s.get("progress") or 0.0)
                bar.progress(min(max(prog, 0.0), 1.0))
                status_placeholder.caption(f"Status: **{s.get('status','?')}** • {int(prog*100)}%")
                if s.get("status") in ("completed","failed"):
                    break
            except Exception as e:
                status_placeholder.caption(f"Error: {e}")
                break
            time.sleep(0.7)

    s = requests.get(f"{API_BASE}/runs/{run_id}", timeout=10).json()
    if s.get("status") == "failed":
        st.error(s.get("error","Run failed"))
        st.stop()

    result = (s or {}).get("result") or {}
    mode = result.get("mode") or task

    if mode == "qa":
        st.subheader("📄 Document Q&A (demo)")
        qa = result.get("qa") or {}
        st.write("**Question:**", qa.get("question","—"))
        st.write("**Answer:**", qa.get("answer","—"))
        st.write("**Confidence:**", qa.get("confidence","—"))
        st.caption("Note: For this minimal demo, the document is optional and PDFs aren't parsed.")
    else:
        st.subheader("📊 Forecast & Suggestion (single stock)")

        # Chart
        series = result.get("series") or {}
        df = pd.DataFrame({
            "date": series.get("dates", []),
            "actual": series.get("actual", []),
            "forecast": series.get("forecast", []),
            "lower": series.get("lower", []),
            "upper": series.get("upper", []),
        })
        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["date"], y=df["actual"], mode="lines", name="Actual"))
            fig.add_trace(go.Scatter(x=df["date"], y=df["forecast"], mode="lines", name="Forecast"))
            # Forecast band
            fig.add_trace(go.Scatter(x=df["date"], y=df["upper"], mode="lines", name="Upper", line=dict(width=0)))
            fig.add_trace(go.Scatter(x=df["date"], y=df["lower"], mode="lines", name="Lower", fill='tonexty', line=dict(width=0)))
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No series available yet.")

        # Minimal suggestion using last step
        try:
            last_actual = df["actual"].iloc[-1] if not df.empty else None
            last_forecast = df["forecast"].iloc[-1] if not df.empty else None
            change = None
            if last_actual is not None and last_forecast is not None and last_actual != 0:
                change = (last_forecast - last_actual) / last_actual

            action = "HOLD"
            reason = "Forecast near current price."
            if change is not None:
                if change > 0.01:
                    action = "BUY"
                    reason = f"Forecast is {change*100:.1f}% above last price."
                elif change < -0.01:
                    action = "SELL"
                    reason = f"Forecast is {abs(change)*100:.1f}% below last price."

            st.markdown(f"### ✅ Suggested Action: **{(action)}** for **{(result.get('input',{}) or {}).get('symbols',[symbol])[0]}**")
            st.caption(reason)

        except Exception:
            st.info("Suggestion unavailable.")

        # Tiny KPIs for demo
        acc = (result.get("metrics", {}).get("accuracy") or {})
        strat = (result.get("metrics", {}).get("strategy") or {})
        k1, k2, k3 = st.columns(3)
        k1.metric("RMSE", acc.get("rmse","—"))
        k2.metric("Directional Acc.", f"{round((acc.get('directional_accuracy') or 0)*100,1)}%")
        k3.metric("Sharpe", strat.get("sharpe","—"))
