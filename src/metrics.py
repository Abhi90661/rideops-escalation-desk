from __future__ import annotations

import numpy as np
import pandas as pd


def week_end_snapshot(week_start: str | pd.Timestamp, df: pd.DataFrame) -> pd.Timestamp:
    """Return the Sunday 23:59:59 snapshot, capped at the extract timestamp."""
    start = pd.Timestamp(week_start).normalize()
    sunday_end = start + pd.Timedelta(days=7) - pd.Timedelta(seconds=1)
    last_date = df["created_at"].max()
    return min(sunday_end, pd.Timestamp(last_date))


def filter_week(df: pd.DataFrame, week: str | pd.Timestamp | None = None) -> pd.DataFrame:
    """Filter tickets by their Monday-start week."""
    if week is None:
        return df
    start = pd.Timestamp(week).normalize()
    start = start - pd.Timedelta(days=start.weekday())
    end = start + pd.Timedelta(days=7)
    return df.loc[df["created_at"].ge(start) & df["created_at"].lt(end)].copy()


def apply_censoring(
    df: pd.DataFrame,
    censor_last_14_days: bool = False,
    as_of: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Exclude tickets created in the last 14 days of the available extract."""
    if not censor_last_14_days:
        return df
    cutoff = pd.Timestamp(as_of).normalize() if as_of is not None else df["created_at"].max().normalize()
    return df.loc[df["created_at"] <= cutoff - pd.Timedelta(days=14)].copy()


def weekly_open_snapshot(df: pd.DataFrame, snapshot: str | pd.Timestamp) -> int:
    at = pd.Timestamp(snapshot)
    return int(((df["created_at"] <= at) & (df["final_closed_at"].isna() | (df["final_closed_at"] > at))).sum())


def monthly_escalation_rate(df: pd.DataFrame) -> pd.Series:
    return df.groupby("month")["esc"].mean().mul(100)


def outcome_counts(df: pd.DataFrame) -> pd.Series:
    return df.loc[df["esc"], "eng_outcome"].value_counts()


def median_close_hours(df: pd.DataFrame, escalated: bool | None = None) -> float:
    subset = df if escalated is None else df[df["esc"].eq(escalated)]
    return float(subset["res_h"].dropna().median())


def escalation_precision(df: pd.DataFrame) -> float:
    esc = df[df["esc"]]
    return float(esc["eng_outcome"].eq("Fixed").mean()) if len(esc) else np.nan


def bounce_rate(df: pd.DataFrame) -> float:
    esc = df[df["esc"]]
    return float(esc["bounce"].mean()) if len(esc) else np.nan


def handoffs_per_escalated(df: pd.DataFrame) -> float:
    esc = df[df["esc"]]
    return float(esc["eng_handoffs"].mean()) if len(esc) else np.nan


def repeat_rate(df: pd.DataFrame) -> float:
    return float(df["repeat14"].mean()) if len(df) else np.nan


def category_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, group in df.groupby("category"):
        esc = group[group["esc"]]
        rows.append({
            "category": category, "volume": len(group),
            "escalation_rate": group["esc"].mean(),
            "bounce_rate": esc["bounce"].mean() if len(esc) else np.nan,
            "repeat_rate": group["repeat14"].mean(),
            "csat": group["csat_score"].mean(),
            "hours_open": group["res_h"].fillna(0).sum(),
        })
    return pd.DataFrame(rows).sort_values("hours_open", ascending=False)


def true_open_backlog_per_100_weekly_tickets(
    df: pd.DataFrame,
    week: str | pd.Timestamp | None = None,
) -> float:
    """Open at week end divided by tickets created that week, per 100 tickets."""
    subset = filter_week(df, week)
    if week is None or subset.empty:
        snapshot = df["created_at"].max().normalize()
        weekly_tickets = len(df)
    else:
        start = pd.Timestamp(week).normalize()
        start = start - pd.Timedelta(days=start.weekday())
        snapshot = week_end_snapshot(start, df)
        weekly_tickets = len(subset)
    open_count = weekly_open_snapshot(df, snapshot)
    return float(open_count / weekly_tickets * 100) if weekly_tickets else np.nan


def reopen_rate(df: pd.DataFrame) -> float:
    return float(df["reopened"].mean()) if len(df) else np.nan


def csat(df: pd.DataFrame) -> float:
    values = pd.to_numeric(df["csat_score"], errors="coerce").dropna()
    return float(values.mean()) if len(values) else np.nan


def section_4_metrics(
    df: pd.DataFrame,
    week: str | pd.Timestamp | None = None,
    censor_last_14_days: bool = False,
    as_of: str | pd.Timestamp | None = None,
) -> dict[str, float | int]:
    """Pure functions for every headline, driver, and guardrail metric."""
    subset = filter_week(df, week)
    subset = apply_censoring(subset, censor_last_14_days, as_of)

    return {
        "true_open_backlog_per_100_weekly_tickets": true_open_backlog_per_100_weekly_tickets(
            subset, week
        ),
        "escalation_precision": escalation_precision(subset),
        "bounce_rate": bounce_rate(subset),
        "handoffs_per_escalated": handoffs_per_escalated(subset),
        "median_escalated_close_h": median_close_hours(subset, True),
        "repeat_contact_rate": repeat_rate(subset),
        "reopen_rate": reopen_rate(subset),
        "csat": csat(subset),
    }


def weekly_scorecard(
    df: pd.DataFrame,
    week: pd.Timestamp | None = None,
    censor_last_14_days: bool = False,
) -> dict:
    subset = filter_week(df, week)
    subset = apply_censoring(subset, censor_last_14_days)
    snapshot = week_end_snapshot(week, df) if week is not None else df["created_at"].max()
    return {
        "backlog": weekly_open_snapshot(df, snapshot),
        "tickets": len(subset),
        "precision": escalation_precision(subset),
        "bounce_rate": bounce_rate(subset),
        "handoffs": handoffs_per_escalated(subset),
        "median_escalated_close_h": median_close_hours(subset, True),
        "repeat_rate": repeat_rate(subset),
        "reopen_rate": reopen_rate(subset),
        "csat": csat(subset),
        "right_censored": censor_last_14_days,
    }

