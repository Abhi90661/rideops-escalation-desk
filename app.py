import streamlit as st
from pathlib import Path
from src.load import load_tickets

st.set_page_config(page_title="RideOps Escalation Desk", layout="wide")
st.title("RideOps Escalation Desk")
st.markdown("Use the pages in the sidebar: **Escalation Desk**, **Scorecard**, **Impact Simulator**, and **Method & Data**.")
uploaded = st.file_uploader(
    "Upload a RideOps CSV (optional)",
    type=["csv"],
    help="CSV replaces the bundled data for this session only.",
)
if uploaded is not None:
    try:
        st.session_state["tickets"] = load_tickets(uploaded)
        st.session_state["upload_name"] = uploaded.name
    except Exception as exc:
        st.error(f"Could not load the uploaded CSV: {exc}")
elif "tickets" not in st.session_state:
    bundled = Path("data/rideops_support_tickets.csv")
    if bundled.exists():
        st.session_state["tickets"] = load_tickets(bundled)
if "tickets" in st.session_state:
    df = st.session_state["tickets"]
    st.success(f"Loaded {len(df):,} tickets. Data range: {df.created_at.min():%d %b} - {df.created_at.max():%d %b %Y}.")
else:
    st.info("Upload the CSV to begin.")

