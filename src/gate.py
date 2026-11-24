from __future__ import annotations

import pandas as pd
from .playbooks import DEFAULT_PLAYBOOK, PLAYBOOKS


def gate_decision(category: str, evidence: dict[str, str], known_match: bool = False, override_reason: str = "") -> str:
    """Return one of the four explicit Escalation Desk verdicts."""
    if known_match:
        return "Attach to known issue"
    if override_reason.strip():
        return "Ready to escalate"
    required = PLAYBOOKS.get(category, DEFAULT_PLAYBOOK)["required"]
    missing = any(not str(evidence.get(key, "")).strip() for key in required)
    return "Not ready: missing evidence" if missing else (
        "Resolve at L1 first" if category in {"Login / access issue", "How-to / feature request", "Cab delay / no-show complaint"} else "Ready to escalate"
    )


def cost_stats(df: pd.DataFrame, category: str) -> dict[str, float]:
    """Describe observed handoff cost and CSAT impact; never predict fix probability."""
    esc = df[(df["category"] == category) & df["esc"]].copy()
    if esc.empty:
        return {"bounce_rate": 0.0, "median_handoff_hours": 57.0, "csat_drop": 0.0}

    bounce_rate = float(esc["bounce"].mean())
    handoff_hours = []
    for handoffs, res_h in zip(esc["eng_handoffs"], esc["res_h"]):
        if pd.notna(handoffs) and pd.notna(res_h) and handoffs > 0:
            handoff_hours.append(float(res_h / handoffs))
    median_handoff_hours = float(pd.Series(handoff_hours).median()) if handoff_hours else 57.0

    esc_csat = pd.to_numeric(esc["csat_score"], errors="coerce").dropna()
    multi_csat = pd.to_numeric(
        esc.loc[esc["eng_handoffs"].gt(1), "csat_score"], errors="coerce"
    ).dropna()
    csat_drop = float(esc_csat.mean() - multi_csat.mean()) if len(multi_csat) else 0.0

    return {
        "bounce_rate": bounce_rate,
        "median_handoff_hours": median_handoff_hours,
        "csat_drop": csat_drop,
    }


def build_handoff_packet(client: str, tier: str, priority: str, category: str, description: str, checked: list[str], evidence: dict[str, str], similar: str = "", impact: str = "") -> str:
    evidence_lines = "\n".join(f"- {key}: {value}" for key, value in evidence.items() if str(value).strip()) or "- None supplied"
    return f"""## Engineering handoff
- Client: {client} ({tier})
- Priority: {priority}
- Category: {category}
- Description: {description}
- Business impact: {impact or 'Not supplied'}

### L1 checks completed
{chr(10).join(f'- {item}' for item in checked) or '- None'}

### Evidence
{evidence_lines}

### Similar tickets
{similar or 'None identified'}
"""

