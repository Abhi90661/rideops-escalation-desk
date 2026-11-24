import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import numpy as np

from src.metrics import (
    apply_censoring,
    bounce_rate,
    category_metrics,
    csat,
    escalation_precision,
    handoffs_per_escalated,
    median_close_hours,
    reopen_rate,
    repeat_rate,
    true_open_backlog_per_100_weekly_tickets,
    weekly_open_snapshot,
    week_end_snapshot,
)

st.title("Scorecard")

df = st.session_state.get("tickets")
if df is None:
    st.warning("Load a CSV on the home page first.")
    st.stop()

extract_last_date = df["created_at"].max().normalize()
extract_end = extract_last_date

weeks = sorted(df["week"].dropna().unique())
if not weeks:
    st.info("No dated tickets are available.")
    st.stop()

def is_complete_week(week_start: pd.Timestamp) -> bool:
    week_sunday = pd.Timestamp(week_start).normalize() + pd.Timedelta(days=6)
    extract_start = df["created_at"].min().normalize()
    return pd.Timestamp(week_start).normalize() >= extract_start and week_sunday <= extract_end

complete_weeks = [week for week in weeks if is_complete_week(pd.Timestamp(week))]
default_week = complete_weeks[-1] if complete_weeks else weeks[-1]

selected_week = st.selectbox(
    "Week",
    weeks,
    index=weeks.index(default_week),
    format_func=lambda value: (
        f"{pd.Timestamp(value).strftime('%d %b %Y')} (partial)"
        if not is_complete_week(pd.Timestamp(value))
        else pd.Timestamp(value).strftime("%d %b %Y")
    ),
)
selected_week = pd.Timestamp(selected_week).normalize()
week_end = selected_week + pd.Timedelta(days=6)

if not is_complete_week(selected_week):
    st.warning(
        "Partial week: backlog per 100 tickets is not comparable to full weeks."
    )

week_mask = df["week"].eq(selected_week)
week_df = df.loc[week_mask].copy()

week_index = weeks.index(selected_week)
prior_weeks = weeks[max(0, week_index - 4):week_index]
if prior_weeks:
    prior_df = df.loc[df["week"].isin(prior_weeks)].copy()
else:
    prior_df = week_df.copy()

extract_end = df["created_at"].max().normalize()
censored = week_end >= extract_end - pd.Timedelta(days=14)
if censored:
    st.caption(
        "Right-censored: tickets created in the final 14 days of the 30 Sep extract "
        "may not have reached final close."
    )

def metric_values(data: pd.DataFrame) -> dict:
    return {
        "Backlog / 100 tickets": true_open_backlog_per_100_weekly_tickets(
            df, selected_week
        ) if data is week_df else np.nan,
        "Escalation precision": escalation_precision(data),
        "Bounce rate": bounce_rate(data),
        "Handoffs": handoffs_per_escalated(data),
        "Escalated close (h)": median_close_hours(data, True),
        "Repeat-contact rate": repeat_rate(data),
        "Reopen rate": reopen_rate(data),
        "CSAT": csat(data),
    }

week_metrics = metric_values(week_df)
if prior_df is week_df:
    prior_metrics = week_metrics
else:
    prior_metrics = {
        "Backlog / 100 tickets": (
            sum(
                true_open_backlog_per_100_weekly_tickets(df, prior_week)
                for prior_week in prior_weeks
            ) / len(prior_weeks)
            if prior_weeks
            else np.nan
        ),
        "Escalation precision": escalation_precision(prior_df),
        "Bounce rate": bounce_rate(prior_df),
        "Handoffs": handoffs_per_escalated(prior_df),
        "Escalated close (h)": median_close_hours(prior_df, True),
        "Repeat-contact rate": repeat_rate(prior_df),
        "Reopen rate": reopen_rate(prior_df),
        "CSAT": csat(prior_df),
    }

st.subheader("This week vs previous 4-week average")
tile_labels = list(week_metrics)
tile_columns = st.columns(4)
for index, label in enumerate(tile_labels):
    current = week_metrics[label]
    baseline = prior_metrics[label]
    if pd.isna(current):
        display = "N/A"
        delta = None
    elif label in {"Escalated close (h)", "Handoffs", "Backlog / 100 tickets"}:
        display = f"{current:.1f}"
        delta = None if pd.isna(baseline) else f"{current - baseline:+.1f}"
    elif label == "CSAT":
        display = f"{current:.2f}"
        delta = None if pd.isna(baseline) else f"{current - baseline:+.2f}"
    else:
        display = f"{current:.1%}"
        delta = None if pd.isna(baseline) else f"{(current - baseline)*100:+.1f} pp"
    tile_columns[index % 4].metric(
        label,
        display,
        delta if delta is not None else "No comparison",
    )

st.subheader("Backlog decomposition")
weekly = (
    df.groupby("week")
    .agg(
        inflow=("ticket_id", "size"),
        median_cycle_h=("res_h", "median"),
    )
    .reset_index()
)
weekly["open_backlog"] = weekly["week"].apply(
    lambda start: weekly_open_snapshot(df, week_end_snapshot(start, df))
)

fig = go.Figure()
fig.add_bar(
    x=weekly["week"],
    y=weekly["inflow"],
    name="Weekly inflow",
    marker_color="#4472C4",
)
fig.add_scatter(
    x=weekly["week"],
    y=weekly["open_backlog"],
    name="Open backlog",
    mode="lines+markers",
    yaxis="y",
    line={"color": "#C44E52", "width": 3},
)
fig.add_scatter(
    x=weekly["week"],
    y=weekly["median_cycle_h"],
    name="Median cycle time (h)",
    mode="lines+markers",
    yaxis="y2",
    line={"color": "#55A868", "width": 3},
)
fig.update_layout(
    title="Inflow, open backlog, and cycle time",
    legend={"orientation": "h"},
    yaxis={"title": "Tickets"},
    yaxis2={
        "title": "Median hours",
        "overlaying": "y",
        "side": "right",
        "showgrid": False,
    },
    height=430,
)
st.plotly_chart(fig, use_container_width=True)
st.caption("The stock is open at week end; median cycle time is the flow speed.")

st.subheader("Escalation funnel")
total = len(df)
escalated = int(df["esc"].sum())
fixed = int(df.loc[df["esc"], "eng_outcome"].eq("Fixed").sum())
duplicates = int(df.loc[df["esc"], "eng_outcome"].eq("Duplicate of known issue").sum())
bounced = int(df["bounce"].sum())
other = max(escalated - fixed - duplicates - bounced, 0)

funnel = pd.DataFrame(
    {
        "Stage": ["All tickets", "Escalated", "Fixed", "Duplicate", "Returned to L1", "Other"],
        "Tickets": [total, escalated, fixed, duplicates, bounced, other],
    }
)
funnel_fig = go.Figure(
    go.Funnel(
        y=funnel["Stage"],
        x=funnel["Tickets"],
        textinfo="value+percent initial",
        marker={"color": ["#4472C4", "#4472C4", "#55A868", "#F2A65A", "#C44E52", "#937860"]},
    )
)
funnel_fig.update_layout(title="Escalation outcomes", height=390)
st.plotly_chart(funnel_fig, use_container_width=True)

st.subheader("Category table")
category_table = category_metrics(df)
st.dataframe(
    category_table.style.format(
        {
            "escalation_rate": "{:.1%}",
            "bounce_rate": "{:.1%}",
            "repeat_rate": "{:.1%}",
            "csat": "{:.2f}",
        }
    ),
    use_container_width=True,
)

st.subheader("Agent coaching")
agent_table = (
    df.groupby("assigned_agent")
    .agg(
        tickets=("ticket_id", "size"),
        escalation_precision=("esc", "mean"),
        reopen_rate=("reopened", "mean"),
        csat=("csat_score", "mean"),
    )
    .reset_index()
)
escalated_df = df[df["esc"]]
precision_by_agent = escalated_df.groupby("assigned_agent")["eng_outcome"].apply(
    lambda values: values.eq("Fixed").mean()
)
agent_table["escalation_precision"] = agent_table["assigned_agent"].map(precision_by_agent)
bounce_by_agent = escalated_df.groupby("assigned_agent")["bounce"].mean()
agent_table["bounce_share"] = agent_table["assigned_agent"].map(bounce_by_agent)

st.caption("For coaching, not ranking.")
st.dataframe(
    agent_table.style.format(
        {
            "escalation_precision": "{:.1%}",
            "bounce_share": "{:.1%}",
            "reopen_rate": "{:.1%}",
            "csat": "{:.2f}",
        }
    ),
    hide_index=True,
    use_container_width=True,
)
st.warning(
    "Fast is not the same as resolved — Karan B had 29.5% reopened tickets, "
    "compared with 4.5% to 9.1% for peers."
)

st.subheader("At-risk open tickets")
open_df = df[df["open"]].copy()
category_medians = df.groupby("category")["res_h"].median()
open_df["age_h"] = (
    extract_end + pd.Timedelta(hours=23, minutes=59, seconds=59) - open_df["created_at"]
).dt.total_seconds() / 3600
open_df["category_median_h"] = open_df["category"].map(category_medians)
open_df["age_vs_category_median"] = (
    open_df["age_h"] / open_df["category_median_h"]
).round(2)

at_risk = open_df[
    [
        "ticket_id",
        "category",
        "priority",
        "created_at",
        "age_h",
        "category_median_h",
        "age_vs_category_median",
        "eng_handoffs",
        "assigned_agent",
        "status",
    ]
].sort_values(["priority", "eng_handoffs", "age_h"], ascending=[True, False, False])

st.dataframe(
    at_risk.style.format(
        {
            "age_h": "{:.1f}",
            "category_median_h": "{:.1f}",
            "age_vs_category_median": "{:.2f}",
        }
    ),
    hide_index=True,
    use_container_width=True,
)
st.caption(f"{len(open_df)} open tickets at the 30 Sep extract.")
