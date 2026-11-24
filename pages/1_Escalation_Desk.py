import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd

from src.playbooks import PLAYBOOKS, DEFAULT_PLAYBOOK
from src.signatures import is_known_issue, similar_signatures
from src.gate import gate_decision, cost_stats, build_handoff_packet

st.title("Escalation Desk")
df = st.session_state.get("tickets")
if df is None:
    st.warning("Load a CSV on the home page first.")
    st.stop()

category = st.selectbox("Category", sorted(df["category"].dropna().unique()))
description = st.text_area(
    "Description",
    "Cancelled bookings still appearing in tomorrow's roster",
)
client = st.selectbox("Client", sorted(df["client_name"].dropna().unique()))
priority = st.selectbox("Priority", ["P1", "P2", "P3", "P4"])
client_tier = df.loc[df["client_name"].eq(client), "client_tier"].iloc[0]

st.subheader("Known-issue radar")
matches = similar_signatures(df, category, description)
known_match = not matches.empty
if not matches.empty:
    known_match = bool(is_known_issue(matches.iloc[0]))

if known_match:
    top = matches.iloc[0]
    radar_columns = [
        col
        for col in ["signature", "similarity", "tickets_14d", "tickets_30d", "duplicates", "last_outcome"]
        if col in matches.columns
    ]
    st.dataframe(matches[radar_columns].head(5), hide_index=True, use_container_width=True)
    st.info(
        f"Recurring issue: {int(top.get('tickets_14d', 0))} tickets in 14 days, "
        f"{int(top.get('duplicates', 0))} marked duplicate. "
        "Check with engineering before filing a new ticket."
    )
    recent_id = str(top.get("open_eng_ticket_id", "") or "")
    if recent_id:
        st.caption(f"Most recent open engineering ticket for this signature: {recent_id}")
    st.caption(
        "Suggested client message: We found an existing known issue and are attaching "
        "your case to it. We will keep you updated while the team confirms the workaround."
    )
else:
    if matches.empty:
        st.caption("No similar past tickets above the similarity threshold.")
    else:
        st.caption("Similar past tickets found, but no confirmed recurring issue")

playbook = PLAYBOOKS.get(category, DEFAULT_PLAYBOOK)
st.subheader("Category checklist")
st.caption(f"{playbook['hypothesis_note']}")

checked = [
    item
    for item in playbook["checklist"]
    if st.checkbox(item, key=f"check_{category}_{item}")
]

evidence = {
    key: st.text_input(label, key=f"evidence_{category}_{key}")
    for key, label in playbook["required"].items()
}
override = st.text_input(
    "Override reason (required only when evidence is missing)",
    key="override_reason",
)

verdict = gate_decision(category, evidence, known_match, override)
verdict_colors = {
    "Resolve at L1 first": "#2E8B57",
    "Attach to known issue": "#4472C4",
    "Not ready: missing evidence": "#D97706",
    "Ready to escalate": "#B91C1C",
}
st.subheader("Verdict")
st.markdown(
    f'<span style="display:inline-block;padding:.35rem .7rem;border-radius:999px;'
    f'background:{verdict_colors[verdict]};color:white;font-weight:700">{verdict}</span>',
    unsafe_allow_html=True,
)

st.subheader("Cost of a bad handoff")
costs = cost_stats(df, category)
cost1, cost2, cost3 = st.columns(3)
cost1.metric("Past bounce rate", f"{costs['bounce_rate']:.1%}")
cost2.metric("Observed h/handoff", f"{costs['median_handoff_hours']:.1f}h")
cost3.metric("CSAT difference", f"{costs['csat_drop']:+.2f}")
st.caption("Historical descriptive facts, not predictions.")

impact = st.text_input("Business impact")

similar = similar_signatures(df, category, description).head(5)
similar_text = "None identified"
if not similar.empty:
    parts = []
    for _, row in similar.iterrows():
        ticket_id = row.get("ticket_id", "")
        outcome = row.get("last_outcome", row.get("eng_outcome", ""))
        hours = row.get("res_h")
        label = str(ticket_id) if pd.notna(ticket_id) else "similar ticket"
        suffix = f"{hours:.1f}h" if isinstance(hours, (int, float)) and pd.notna(hours) else "hours unavailable"
        parts.append(f"{label} ({outcome or 'unknown outcome'}, {suffix})")
    similar_text = "; ".join(parts)

packet = build_handoff_packet(
    client=client,
    tier=client_tier,
    priority=priority,
    category=category,
    description=description,
    checked=checked,
    evidence=evidence,
    similar=similar_text,
    impact=impact,
)

st.subheader("Engineering handoff packet")
st.code(packet, language="markdown")
evidence_complete = all(str(value).strip() for value in evidence.values())
packet_allowed = evidence_complete or bool(override.strip())

packet_json = json.dumps(packet)
components.html(
    f"""
    <button id="copy" {'disabled' if not packet_allowed else ''}
      style="padding:.45rem .8rem;border:1px solid #ccc;border-radius:.35rem;">
      Copy packet
    </button>
    <script>
      const packet = {packet_json};
      document.getElementById("copy").addEventListener("click", async () => {{
        await navigator.clipboard.writeText(packet);
      }});
    </script>
    """,
    height=55,
)
st.download_button(
    "Download packet",
    packet,
    file_name="engineering_handoff.md",
    mime="text/markdown",
    disabled=not packet_allowed,
)

st.subheader("Similar past tickets")
if not similar.empty:
    columns = [
        col
        for col in ["ticket_id", "description", "eng_outcome", "res_h", "similarity"]
        if col in similar.columns
    ]
    display = similar[columns].head(5).copy()
    display = display.rename(columns={"eng_outcome": "outcome", "res_h": "hours_open"})
    st.dataframe(display, hide_index=True, use_container_width=True)
else:
    st.caption("No similar past tickets above the 0.6 threshold.")
