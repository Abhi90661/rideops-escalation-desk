import streamlit as st

st.title("Method & Data")

st.subheader("Success metrics")
st.markdown(
    """
- **8-week headline target:** -15% from process changes (-30% if repeat contacts also fall).
- **True open backlog per 100 weekly tickets:** open tickets at the Sunday week-end snapshot,
  divided by tickets created in that Monday-to-Sunday week, multiplied by 100.
- **Escalation precision:** escalations ending `Fixed` / all escalations.
- **Bounce rate:** outcomes `Insufficient info - returned to L1` or
  `Config issue - returned to L1` / all escalations.
- **Handoffs per escalated ticket:** total engineering handoffs / escalated tickets.
- **Escalated median close:** median final-close minus created time for escalated tickets.
- **Repeat-contact rate:** same `client_id` and `category` within 14 days of a prior ticket.
- **Reopen rate:** tickets with `reopen_count > 0` / all tickets.
- **CSAT:** mean response rating, using only available scores.
"""
)

st.subheader("Censoring")
st.warning(
    "September is right-censored. Tickets still open on 30 Sep 2026 have no final close "
    "and are excluded from closed-time calculations, so September cycle time is understated "
    "and the real increase is likely larger."
)
st.caption(
    "The Scorecard uses end-of-Sunday snapshots for Monday-to-Sunday weeks. "
    "The written analysis uses Thursday-based weekly snapshots (2 Jul + 7 days), "
    "so the two sets of open-ticket numbers differ slightly."
)

st.subheader("Assumptions and caveats")
st.markdown(
    """
1. Engineering outcomes `Insufficient info` and `Config issue` are treated as avoidable by
   better L1 preparation. Engineering's verdict is taken as truth.
2. There are no timestamps for individual handoffs, so 57h per handoff is inferred from
   resolution time divided by handoff count; it is not proven causal.
3. September remains right-censored, as described above.
4. Reopened tickets count as open in the true backlog.
5. CSAT is present for about 45% of tickets and is directional only.
6. Agent-level and same-description comparisons have small samples. Use them for coaching,
   not as employee verdicts.
7. All data is fictional. Any causal claim is a hypothesis for the pilot to test.
8. Category checklists are domain hypotheses, not findings in the data.
"""
)

st.subheader("Source and privacy")
st.markdown(
    """
- Source: `data/rideops_support_tickets.csv`
- Dictionary: `data/rideops_data_dictionary.csv`
- All timestamps are parsed as IST-naive datetimes.
- The data is confidential. Keep the repository private and do not publish the CSV.
- Uploading a CSV replaces the bundled dataset for the current session.
- The data has no parent-ticket link, so duplicate tickets cannot be traced to one engineering ticket.
"""
)

st.subheader("Data quality")
df = st.session_state.get("tickets")
if df is None:
    st.info("Load or upload a CSV on the home page.")
else:
    st.dataframe(
        df[
            [
                "ticket_id",
                "created_at",
                "first_response_at",
                "first_closed_at",
                "final_closed_at",
                "csat_score",
            ]
        ].isna().sum().rename_axis("field").reset_index(name="missing_count"),
        hide_index=True,
        use_container_width=True,
    )
