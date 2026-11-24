from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.load import load_tickets
from src.metrics import (
    weekly_open_snapshot,
    monthly_escalation_rate,
    outcome_counts,
    true_open_backlog_per_100_weekly_tickets,
    escalation_precision,
    bounce_rate,
    handoffs_per_escalated,
    median_close_hours,
    repeat_rate,
    reopen_rate,
    csat,
    filter_week,
    apply_censoring,
    section_4_metrics,
    week_end_snapshot,
)
from src.signatures import normalize_description, signature_stats, similar_signatures, eng_ticket_repeat_report, is_known_issue
from src.playbooks import PLAYBOOKS, DEFAULT_PLAYBOOK
from src.gate import gate_decision, cost_stats, build_handoff_packet
from src.simulate import simulate, HANDOFF_COST_HOURS

DATA = Path(__file__).parents[1] / "data" / "rideops_support_tickets.csv"

def test_acceptance_metrics():
    df = load_tickets(DATA)
    assert len(df) == 1444
    assert weekly_open_snapshot(df, "2026-07-09") == 23
    assert weekly_open_snapshot(df, "2026-09-24") == 50
    rates = monthly_escalation_rate(df)
    assert round(rates["2026-07"], 1) == 37.4
    assert round(rates["2026-08"], 1) == 32.7
    assert round(rates["2026-09"], 1) == 31.9
    assert outcome_counts(df).to_dict() == {
        "Fixed": 211, "Insufficient info - returned to L1": 89,
        "Config issue - returned to L1": 84, "Duplicate of known issue": 56,
        "Not a bug - how-to": 24, "Not reproducible": 22,
    }

def test_repeat_and_reopen_derivations():
    df = load_tickets(DATA)
    karan = df[df.assigned_agent.eq("Karan B")]
    assert round(karan.reopened.mean() * 100, 1) == 29.5
    assert df.repeat14.dtype == bool


def test_load_derivations_and_missing_values():
    df = load_tickets(DATA)

    assert len(df) == 1444
    assert df["esc"].dtype == bool
    assert df["reopened"].dtype == bool
    assert df["bounce"].dtype == bool
    assert df["avoidable"].dtype == bool
    assert df["repeat14"].dtype == bool

    assert df["first_res_h"].isna().sum() == 5
    assert df["first_closed_at"].isna().sum() == 42
    assert df["final_closed_at"].isna().sum() == 48

    assert df["res_h"].isna().sum() == 48
    assert df["frt_h"].equals(df["first_res_h"])
    assert df["bounce"].sum() == 173
    assert df["avoidable"].sum() == 275


def test_timestamps_week_month_and_ist_naive():
    df = load_tickets(DATA)

    for column in ["created_at", "first_response_at", "first_closed_at", "final_closed_at"]:
        assert df[column].dt.tz is None

    assert df["week"].dt.dayofweek.unique().tolist() == [0]
    assert df["month"].eq(df["created_at"].dt.to_period("M").astype(str)).all()


def test_section_4_real_data_metrics():
    df = load_tickets(DATA)
    metrics = section_4_metrics(df)

    assert round(escalation_precision(df) * 100, 1) == 43.4
    assert round(bounce_rate(df) * 100, 1) == 35.6
    assert round(handoffs_per_escalated(df), 2) == 1.60
    assert round(median_close_hours(df, True), 1) == 86.8
    assert round(repeat_rate(df) * 100, 1) == 19.0
    assert round(reopen_rate(df) * 100, 1) == 10.5
    assert round(csat(df), 2) == 3.70
    assert set(metrics) >= {
        "true_open_backlog_per_100_weekly_tickets",
        "escalation_precision",
        "bounce_rate",
        "handoffs_per_escalated",
        "median_escalated_close_h",
        "repeat_contact_rate",
        "reopen_rate",
        "csat",
    }


def test_week_filter_and_censoring():
    df = load_tickets(DATA)
    week = pd.Timestamp("2026-09-21")
    filtered = filter_week(df, week)
    assert len(filtered) > 0
    assert filtered["created_at"].min() >= pd.Timestamp("2026-09-21")
    assert filtered["created_at"].max() < pd.Timestamp("2026-09-28")

    uncensored = apply_censoring(df, False)
    censored = apply_censoring(df, True)
    cutoff = df["created_at"].max().normalize() - pd.Timedelta(days=14)
    assert len(censored) == int(df["created_at"].le(cutoff).sum())
    assert censored["created_at"].max() <= cutoff


def test_true_open_backlog_per_100_weekly_tickets():
    df = load_tickets(DATA)
    july = true_open_backlog_per_100_weekly_tickets(df, "2026-07-06")
    september = true_open_backlog_per_100_weekly_tickets(df, "2026-09-21")
    assert july >= 0
    assert september >= 0


def test_sunday_end_snapshot_for_complete_week():
    df = load_tickets(DATA)
    week = pd.Timestamp("2026-09-21")
    snapshot = week_end_snapshot(week, df)
    assert snapshot == pd.Timestamp("2026-09-27 23:59:59")
    assert weekly_open_snapshot(df, snapshot) == 43
    backlog = true_open_backlog_per_100_weekly_tickets(df, week)
    assert round(backlog, 1) == 31.9


def test_description_normalization():
    assert normalize_description("Cancelled 42 bookings at 10 PM") == "cancelled N bookings at SHIFT"
    assert normalize_description("Frozen GPS at 6 AM") == "frozen gps at SHIFT"


def test_signature_stats_and_matches():
    df = load_tickets(DATA)

    report = eng_ticket_repeat_report(df)
    assert report["repeats"] is False

    stats = signature_stats(df)
    assert {"tickets_14d", "tickets_30d", "escalated", "duplicates", "linked_eng_tickets"} <= set(stats.columns)

    matches = similar_signatures(
        df,
        "Roster / booking not syncing",
        "Cancelled bookings still appearing in tomorrow's roster",
    )
    assert not matches.empty
    assert matches.iloc[0]["signature"] in {
        "cancelled bookings still appearing in tomorrow's roster",
        "cancelled bookings still appearing in tomorrowN roster",
    }


def test_gate_verdicts_and_handoff_packet():
    assert "Hypothesis" in " ".join([
        playbook.get("hypothesis_note", "") for playbook in PLAYBOOKS.values()
    ])
    assert gate_decision(
        "Roster / booking not syncing",
        {"trip_ids": "", "shift": "", "screenshot": ""},
    ) == "Not ready: missing evidence"

    assert gate_decision(
        "Roster / booking not syncing",
        {"trip_ids": "TR-1", "shift": "10 PM", "screenshot": "attached"},
    ) == "Ready to escalate"

    assert gate_decision(
        "Login / access issue",
        {"user": "jane", "role": "admin", "affected_users": "1"},
    ) == "Resolve at L1 first"

    assert gate_decision(
        "Any unknown category",
        {},
        known_match=True,
    ) == "Attach to known issue"

    df = load_tickets(DATA)
    stats = cost_stats(df, "Roster / booking not syncing")
    assert stats["bounce_rate"] > 0
    assert stats["median_handoff_hours"] > 0

    packet = build_handoff_packet(
        client="Apex",
        tier="Enterprise",
        priority="P2",
        category="Roster / booking not syncing",
        description="Roster mismatch",
        checked=["Trip IDs"],
        evidence={"trip_ids": "TR-1"},
        similar="SUP-10034",
        impact="20 employees affected",
    )
    assert "## Engineering handoff" in packet
    assert "TR-1" in packet
    assert "probability" not in packet.lower()


def test_known_issue_requires_duplicate_or_recent_open_escalation():
    assert is_known_issue({"duplicates": 1, "open_escalations_14d": 0}) is True
    assert is_known_issue({"duplicates": 0, "open_escalations_14d": 1}) is True
    assert is_known_issue({"duplicates": 0, "open_escalations_14d": 0}) is False

    df = load_tickets(DATA)
    duplicate_match = similar_signatures(
        df,
        "Report export failing",
        "Scheduled report email not received",
    )
    if not duplicate_match.empty:
        row = duplicate_match.iloc[0]
        if int(row["duplicates"]) >= 1:
            assert gate_decision(
                "Report export failing",
                {"report_type": "scheduled", "date_range": "7 days", "retry_result": "failed"},
                known_match=is_known_issue(row),
            ) == "Attach to known issue"

    no_issue_match = pd.Series({
        "duplicates": 0,
        "open_escalations_14d": 0,
    })
    assert is_known_issue(no_issue_match) is False


def test_conservative_impact_simulation():
    df = load_tickets(DATA)
    result = simulate(df)

    assert HANDOFF_COST_HOURS == 57.0
    assert result["actual_ticket_hours"] > 0
    assert result["scenario_ticket_hours"] < result["actual_ticket_hours"]
    assert result["hours_saved"] > 0
    assert result["scenario_precision"] > result["actual_precision"]
    assert result["scenario_handoffs"] < result["actual_handoffs"]

    baseline = simulate(
        df,
        prevent_bounces=0,
        convert_duplicates=0,
        convert_howto=0,
    )
    assert round(baseline["hours_saved"], 6) == 0
    assert 0.63 <= result["scenario_precision"] <= 0.65

