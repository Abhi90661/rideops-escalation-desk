from __future__ import annotations

from pathlib import Path
import pandas as pd

DATE_COLUMNS = ["created_at", "first_response_at", "first_closed_at", "final_closed_at"]


def load_tickets(source: str | Path | object) -> pd.DataFrame:
    """Load and derive the canonical ticket dataset from a path or file-like object."""
    df = pd.read_csv(source)
    for column in DATE_COLUMNS:
        df[column] = pd.to_datetime(df[column], errors="coerce")
    df["escalated"] = df["escalated_to_eng"].fillna("").str.lower().eq("yes")
    df["esc"] = df["escalated"]
    df["reopened"] = pd.to_numeric(df["reopen_count"], errors="coerce").fillna(0).gt(0)
    df["eng_handoffs"] = pd.to_numeric(df["eng_handoffs"], errors="coerce").fillna(0).astype(int)
    df["csat_score"] = pd.to_numeric(df["csat_score"], errors="coerce")
    df["res_h"] = (df["final_closed_at"] - df["created_at"]).dt.total_seconds() / 3600
    df["first_res_h"] = (df["first_response_at"] - df["created_at"]).dt.total_seconds() / 3600
    df["frt_h"] = df["first_res_h"]
    df["week"] = df["created_at"].dt.normalize() - pd.to_timedelta(
        df["created_at"].dt.weekday, unit="D"
    )
    df["month"] = df["created_at"].dt.to_period("M").astype(str)
    outcomes = df["eng_outcome"].fillna("")
    df["bounce"] = outcomes.str.startswith(("Insufficient info", "Config issue"))
    df["avoidable"] = df["esc"] & ~outcomes.eq("Fixed")
    df["open"] = df["final_closed_at"].isna()
    df["repeat14"] = _repeat_contact(df)
    return df


def _repeat_contact(df: pd.DataFrame) -> pd.Series:
    ordered = df.sort_values(["client_id", "category", "created_at"])
    previous = ordered.groupby(["client_id", "category"])["created_at"].shift()
    result = (ordered["created_at"] - previous).dt.total_seconds().div(86400).le(14)
    result = result.fillna(False)
    return result.reindex(df.index).fillna(False)

