from __future__ import annotations

import pandas as pd


HANDOFF_COST_HOURS = 57.0
L1_WORKAROUND_HOURS = 20.0


def _median_or_zero(values: pd.Series) -> float:
    values = values.dropna()
    return float(values.median()) if len(values) else 0.0


def simulate(
    df: pd.DataFrame,
    prevent_bounces: float = 0.40,
    convert_duplicates: float = 0.50,
    l1_workaround_hours: float = L1_WORKAROUND_HOURS,
    convert_howto: float = 0.50,
    inflow_growth: float = 0.0,
    handoff_cost_hours: float = HANDOFF_COST_HOURS,
) -> dict[str, float]:
    """Replay conservative process changes against observed Q3 ticket-hours."""
    esc = df[df["esc"]].copy()
    if len(esc) == 0:
        raise ValueError("No escalated tickets available for simulation")

    bounce = esc[esc["bounce"]]
    extra_bounce_handoffs = int(
        (bounce["eng_handoffs"].fillna(0).astype(int) - 1).clip(lower=0).sum()
    )

    duplicates = esc[esc["eng_outcome"].eq("Duplicate of known issue")]
    howto = esc[
        esc["eng_outcome"].isin(["Not a bug - how-to", "Not reproducible"])
    ]

    saved_bounce_h = prevent_bounces * extra_bounce_handoffs * handoff_cost_hours

    duplicate_median = _median_or_zero(duplicates["res_h"])
    duplicate_saved_per_ticket = max(0.0, duplicate_median - l1_workaround_hours)
    saved_duplicate_h = convert_duplicates * len(duplicates) * duplicate_saved_per_ticket

    other_median = _median_or_zero(howto["res_h"])
    other_saved_per_ticket = max(0.0, other_median - l1_workaround_hours)
    saved_howto_h = convert_howto * len(howto) * other_saved_per_ticket

    hours_saved = saved_bounce_h + saved_duplicate_h + saved_howto_h
    actual_hours = float(df["res_h"].fillna(0).sum())
    inflow_added_hours = actual_hours * inflow_growth
    scenario_hours = max(0.0, actual_hours + inflow_added_hours - hours_saved)

    observed_days = max(
        1.0,
        (df["created_at"].max().normalize() - df["created_at"].min().normalize()).total_seconds()
        / 86400,
    )
    actual_average_backlog = actual_hours / 24 / observed_days
    scenario_average_backlog = scenario_hours / 24 / observed_days
    average_backlog_change = scenario_average_backlog - actual_average_backlog

    fixed_count = int(esc["eng_outcome"].eq("Fixed").sum())
    bounce_tickets = int(len(bounce))
    duplicate_count = int(len(duplicates))
    howto_count = int(len(howto))
    total_escalations = int(len(esc))

    precision_actual = fixed_count / len(esc)
    scenario_fixed = fixed_count + prevent_bounces * bounce_tickets
    scenario_escalations = (
        total_escalations
        - convert_duplicates * duplicate_count
        - convert_howto * howto_count
    )
    scenario_escalations = max(1.0, scenario_escalations)
    precision_scenario = min(
        1.0,
        scenario_fixed / scenario_escalations,
    )

    actual_handoffs = float(esc["eng_handoffs"].fillna(0).sum())
    scenario_handoffs = max(
        0.0,
        actual_handoffs - prevent_bounces * extra_bounce_handoffs,
    )
    handoffs_actual = actual_handoffs / len(esc)
    handoffs_scenario = scenario_handoffs / scenario_escalations

    return {
        "actual_ticket_hours": actual_hours,
        "scenario_ticket_hours": scenario_hours,
        "ticket_hours_change": scenario_hours - actual_hours,
        "hours_saved": float(hours_saved),
        "saved_bounce_h": float(saved_bounce_h),
        "saved_duplicate_h": float(saved_duplicate_h),
        "saved_howto_h": float(saved_howto_h),
        "actual_average_backlog": float(actual_average_backlog),
        "scenario_average_backlog": float(scenario_average_backlog),
        "average_backlog_change": float(average_backlog_change),
        "actual_precision": float(precision_actual),
        "scenario_precision": float(precision_scenario),
        "precision_change": float(precision_scenario - precision_actual),
        "actual_handoffs": float(handoffs_actual),
        "scenario_handoffs": float(handoffs_scenario),
        "handoffs_change": float(handoffs_scenario - handoffs_actual),
        "extra_bounce_handoffs": float(extra_bounce_handoffs),
    }

