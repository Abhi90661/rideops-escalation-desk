import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.simulate import HANDOFF_COST_HOURS, L1_WORKAROUND_HOURS, simulate

st.title("Impact Simulator")

df = st.session_state.get("tickets")
if df is None:
    st.warning("Load a CSV on the home page first.")
    st.stop()

st.warning(
    "Estimate. Assumes handoff cost is constant at about 57h and that prevented "
    "bounces would have been Fixed in one pass."
)

prevent = st.slider(
    "% of bounce escalations prevented",
    min_value=0,
    max_value=100,
    value=40,
) / 100
duplicates = st.slider(
    "% of duplicate escalations attached to known issues",
    min_value=0,
    max_value=100,
    value=50,
) / 100
howto = st.slider(
    "% of how-to and not-reproducible escalations resolved at L1",
    min_value=0,
    max_value=100,
    value=50,
) / 100
growth = st.select_slider(
    "Inflow growth scenario",
    options=[0.0, 0.15],
    value=0.0,
    format_func=lambda value: f"{value:.0%}",
)

handoff_cost = st.number_input(
    "Handoff cost (hours)",
    min_value=0.0,
    max_value=200.0,
    value=HANDOFF_COST_HOURS,
    step=1.0,
)
workaround_hours = st.number_input(
    "L1 workaround speed (hours)",
    min_value=1.0,
    max_value=168.0,
    value=L1_WORKAROUND_HOURS,
    step=1.0,
)

result = simulate(
    df,
    prevent_bounces=prevent,
    convert_duplicates=duplicates,
    l1_workaround_hours=workaround_hours,
    convert_howto=howto,
    inflow_growth=growth,
    handoff_cost_hours=handoff_cost,
)

st.subheader("Estimated change versus actual Q3")
hours_col, backlog_col, precision_col, handoff_col = st.columns(4)
hours_col.metric(
    "Ticket-hours open",
    f"{result['scenario_ticket_hours']:,.0f}",
    f"{result['ticket_hours_change']:+,.0f}h",
)
backlog_col.metric(
    "Average backlog",
    f"{result['scenario_average_backlog']:,.1f}",
    f"{result['average_backlog_change']:+,.1f} tickets",
)
precision_col.metric(
    "Escalation precision",
    f"{result['scenario_precision']:.1%}",
    f"{result['precision_change']:+.1%}",
)
handoff_col.metric(
    "Handoffs / escalated",
    f"{result['scenario_handoffs']:.2f}",
    f"{result['handoffs_change']:+.2f}",
)

st.caption(
    f"Exact components: bounce savings "
    f"{result['saved_bounce_h']:,.0f}h; duplicate savings "
    f"{result['saved_duplicate_h']:,.0f}h; how-to/not-reproducible savings "
    f"{result['saved_howto_h']:,.0f}h."
)
st.caption(
    "At the default assumptions, average backlog falls about 12% "
    "(29.6 to 26.0 tickets). This alone does not reach a 30% reduction; "
    "the rest depends on fewer repeat tickets and faster engineering turnaround, "
    "which this simulator does not model."
)

comparison = pd.DataFrame(
    {
        "Scenario": ["Actual", "Simulated"],
        "Ticket-hours": [
            result["actual_ticket_hours"],
            result["scenario_ticket_hours"],
        ],
        "Average backlog": [
            result["actual_average_backlog"],
            result["scenario_average_backlog"],
        ],
    }
)

chart = go.Figure(
    data=[
        go.Bar(
            name="Ticket-hours",
            x=comparison["Scenario"],
            y=comparison["Ticket-hours"],
            marker_color=["#4472C4", "#55A868"],
            yaxis="y",
        )
    ]
)
chart.update_layout(
    title="Actual vs simulated total ticket-hours",
    yaxis={"title": "Ticket-hours"},
    height=400,
)
st.plotly_chart(chart, use_container_width=True)

with st.expander("Method and assumptions"):
    st.markdown(
        f"""
- Actual ticket-hours: **{result['actual_ticket_hours']:,.0f}h**
- Observed extra bounce handoffs: **{result['extra_bounce_handoffs']:,.0f}**
- Prevented bounce savings: extra bounce handoffs x selected percentage x handoff cost.
- Duplicate savings: selected percentage x duplicate count x max(observed duplicate median - 20h, 0).
- How-to/not-reproducible savings: selected percentage x outcome count x max(observed median - 20h, 0).
- Average backlog uses: ticket-hours / 24 / observed calendar days.
- Inflow growth adds the selected percentage to actual ticket-hours (simple scaling).
- Open tickets at 30 Sep have no final-close timestamp and contribute no resolved ticket-hours.
"""
    )

