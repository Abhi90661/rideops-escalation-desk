from __future__ import annotations

import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_SHIFT = re.compile(r"\b(?:[01]?\d|2[0-3])\s*(?:AM|PM)\b", re.I)
_DIGIT = re.compile(r"\d+")


def normalize_description(text: str) -> str:
    """Normalize templated ticket text while preserving human-readable structure."""
    text = str(text).lower()
    text = _SHIFT.sub("SHIFT", text)
    text = _DIGIT.sub("N", text)
    return " ".join(text.split())


def add_signatures(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["signature"] = result["description"].map(normalize_description)
    return result


def eng_ticket_repeat_report(df: pd.DataFrame) -> dict:
    """Return whether engineering IDs link multiple support tickets."""
    ids = pd.to_numeric(df["eng_ticket_id"].astype("string").str.extract(r"(\d+)")[0], errors="coerce")
    repeated = ids.notna() & ids.duplicated(keep=False)
    if repeated.any():
        return {"repeats": True, "linked_ticket_count": int(repeated.sum())}
    return {"repeats": False, "linked_ticket_count": 0}


def engineering_ticket_links(df: pd.DataFrame) -> pd.Series:
    """Build a signature's engineering-ticket links, preferring open or fixed IDs."""
    data = add_signatures(df)
    output = {}
    for signature, group in data.groupby("signature"):
        ids = group["eng_ticket_id"].dropna().astype(str)
        ids = sorted(set(ids[ids.str.strip().ne("")]))
        output[signature] = ", ".join(ids)
    return pd.Series(output, name="linked_eng_tickets")


def is_known_issue(match_row: pd.Series | dict) -> bool:
    """A recurring issue needs a duplicate outcome or recent open engineering ticket."""
    row = pd.Series(match_row) if isinstance(match_row, dict) else match_row
    duplicates = int(row.get("duplicates", 0) or 0)
    open_last_14 = int(row.get("open_escalations_14d", 0) or 0)
    return duplicates >= 1 or open_last_14 >= 1


def signature_stats(df: pd.DataFrame, as_of: str | pd.Timestamp | None = None) -> pd.DataFrame:
    """Cluster exact signatures within category and compute rolling counts."""
    data = add_signatures(df)
    max_date = pd.Timestamp(as_of).normalize() if as_of is not None else data["created_at"].max().normalize()
    rows = []
    for (category, signature), group in data.groupby(["category", "signature"]):
        rows.append({
            "category": category, "signature": signature,
            "tickets_14d": int((group["created_at"] >= max_date - pd.Timedelta(days=14)).sum()),
            "tickets_30d": int((group["created_at"] >= max_date - pd.Timedelta(days=30)).sum()),
            "escalated": int(group["esc"].sum()),
            "duplicates": int(group["eng_outcome"].eq("Duplicate of known issue").sum()),
            "linked_eng_tickets": _linked_eng_tickets(group),
            "last_outcome": group.sort_values("created_at").iloc[-1]["eng_outcome"] if group["eng_outcome"].notna().any() else "",
        })
    return pd.DataFrame(rows).sort_values(["duplicates", "tickets_14d"], ascending=False)


def similar_signatures(df: pd.DataFrame, category: str, description: str, threshold: float = .6) -> pd.DataFrame:
    """Find exact and TF-IDF near matches within the selected category."""
    data = add_signatures(df)
    category_data = data[data["category"].eq(category)]
    pool = category_data.drop_duplicates("signature")
    if pool.empty:
        return pool.assign(similarity=pd.Series(dtype=float))

    normalized = normalize_description(description)
    texts = pool["signature"].tolist() + [normalize_description(description)]
    matrix = TfidfVectorizer(ngram_range=(1, 2)).fit_transform(texts)
    scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    result = pool.assign(similarity=scores)
    exact = normalize_description(description)
    result["similarity"] = result.apply(
        lambda row: 1.0 if row["signature"] == exact else row["similarity"], axis=1
    )
    result = result[result["similarity"].ge(threshold)].sort_values("similarity", ascending=False)

    stats = signature_stats(df)
    stats = stats[stats["category"].eq(category)]
    if len(result):
        result = result.merge(
            stats[["signature", "tickets_14d", "tickets_30d", "escalated", "duplicates", "linked_eng_tickets", "last_outcome"]],
            on="signature",
            how="left",
        )

    if len(result):
        open_mask = (
            df["esc"]
            & df["status"].eq("Open - with Engineering")
            & (df["created_at"] >= df["created_at"].max().normalize() - pd.Timedelta(days=14))
        )
        open_df = add_signatures(df.loc[open_mask])
        open_rows = []
        for (category, signature), group in open_df.groupby(["category", "signature"]):
            recent = group.sort_values("created_at").iloc[-1]
            open_rows.append({
                "category": category,
                "signature": signature,
                "open_escalations_14d": int(len(group)),
                "open_eng_ticket_id": (
                    str(recent["eng_ticket_id"])
                    if pd.notna(recent["eng_ticket_id"])
                    else ""
                ),
            })
        open_counts = pd.DataFrame(open_rows)
        if open_counts.empty:
            result["open_escalations_14d"] = 0
            result["open_eng_ticket_id"] = ""
        else:
            result = result.merge(
                open_counts,
                on=["category", "signature"],
                how="left",
            )
        result["open_escalations_14d"] = result["open_escalations_14d"].fillna(0).astype(int)
        result["open_eng_ticket_id"] = result["open_eng_ticket_id"].fillna("")
    return result


def _linked_eng_tickets(group: pd.DataFrame) -> str:
    ids = group["eng_ticket_id"].dropna().astype(str)
    ids = sorted(set(ids[ids.str.strip().ne("")]))
    return ", ".join(ids)

