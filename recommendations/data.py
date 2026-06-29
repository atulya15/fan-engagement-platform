"""
recommendations/data.py
=========================
Loads interaction data and builds the structures the recommenders need:
a sparse implicit-feedback user-item matrix, a temporal train/test
split, and content feature vectors for widgets.

HONEST SCALE CAVEAT, stated once here and referenced everywhere else
in this module: the catalog is only 60 widgets. A "Top-10
recommendation" therefore covers ~17% of the entire catalog -- Recall@10
and NDCG@10 will look much higher here than they would against a
real-world catalog of thousands of items. The methodology (ALS,
content similarity, hybrid ranking, temporal split) is the same either
way; the absolute metric VALUES are not comparable to a production
system with a larger catalog, and shouldn't be presented as if they were.
"""

from datetime import timedelta

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from metrics.db import run_query

# Implicit-feedback confidence weights by event type, mirroring the
# POINTS_MAP weighting already used in generate_data.py's gamification
# scoring -- a completion is a much stronger preference signal than a
# passive impression.
EVENT_WEIGHT = {"impression": 1, "interaction": 5, "completion": 10}


def load_events() -> pd.DataFrame:
    """
    run_query_chunked's `chunksize` only batches the CLIENT-SIDE fetch
    over an already-running query -- it does nothing about how long
    that single statement takes to EXECUTE on the server, which is
    exactly what free-tier Supabase's statement_timeout was hitting
    here on the full ~2M-row 3-table join (confirmed: indexes already
    exist on every join key in schema.sql, so this isn't a missing-
    index problem, just more join than the free-tier compute tier can
    finish inside one statement). Splitting into monthly WHERE-bounded
    queries keeps each individual statement small enough to finish
    well under the timeout, at the cost of N round trips instead of 1.
    """
    bounds = run_query(
        "SELECT MIN(event_timestamp) AS lo, MAX(event_timestamp) AS hi FROM widget_events"
    )
    lo, hi = pd.to_datetime(bounds["lo"].iloc[0]), pd.to_datetime(bounds["hi"].iloc[0])

    sql = """
    SELECT we.user_id, we.widget_id, we.event_type, we.event_timestamp,
           w.widget_type, w.sport, w.launch_date,
           u.user_segment, u.acquisition_channel, u.signup_date
    FROM widget_events we
    JOIN widgets w ON w.widget_id = we.widget_id
    JOIN users u ON u.user_id = we.user_id
    WHERE we.event_timestamp >= %(start)s AND we.event_timestamp < %(end)s
    """
    chunks = []
    start = lo
    while start < hi:
        end = min(start + timedelta(days=30), hi + timedelta(seconds=1))
        chunk = run_query(sql, params={"start": start, "end": end})
        if len(chunk) > 0:
            chunks.append(chunk)
        start = end

    df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    df["event_timestamp"] = pd.to_datetime(df["event_timestamp"])
    df["launch_date"] = pd.to_datetime(df["launch_date"])
    df["signup_date"] = pd.to_datetime(df["signup_date"])
    return df


def temporal_split(df: pd.DataFrame, train_frac: float = 10 / 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits by TIME, not randomly -- train on the first ~10 months,
    test on the last ~2. A random split would leak future information
    into training (a model "trained" on a user's month-11 behavior to
    predict their month-11 behavior is cheating); a temporal split is
    the only honest way to evaluate a recommender that will actually
    run on unseen future interactions.
    """
    min_ts, max_ts = df["event_timestamp"].min(), df["event_timestamp"].max()
    cutoff = min_ts + (max_ts - min_ts) * train_frac
    train = df[df["event_timestamp"] < cutoff].copy()
    test = df[df["event_timestamp"] >= cutoff].copy()
    return train, test


def build_interaction_matrix(df: pd.DataFrame, user_ids: list[int], widget_ids: list[int]) -> tuple[csr_matrix, dict, dict]:
    """
    Builds a (n_users x n_widgets) sparse confidence matrix from
    weighted event counts. Returns the matrix plus id<->index maps,
    since `implicit`'s ALS works on positional indices, not raw IDs.
    """
    user_idx = {uid: i for i, uid in enumerate(user_ids)}
    widget_idx = {wid: i for i, wid in enumerate(widget_ids)}

    weights = df["event_type"].map(EVENT_WEIGHT).fillna(0)
    grouped = (
        pd.DataFrame({"user_id": df["user_id"], "widget_id": df["widget_id"], "weight": weights})
        .groupby(["user_id", "widget_id"], as_index=False)["weight"].sum()
    )
    grouped = grouped[grouped["user_id"].isin(user_idx) & grouped["widget_id"].isin(widget_idx)]

    rows = grouped["user_id"].map(user_idx).to_numpy()
    cols = grouped["widget_id"].map(widget_idx).to_numpy()
    vals = grouped["weight"].to_numpy()

    matrix = csr_matrix((vals, (rows, cols)), shape=(len(user_ids), len(widget_ids)))
    return matrix, user_idx, widget_idx


def build_widget_features(widget_meta: pd.DataFrame) -> pd.DataFrame:
    """
    One-hot widget_type + sport -> a content feature vector per widget,
    used for content-based similarity and as hybrid-ranker features.
    """
    meta = widget_meta.drop_duplicates("widget_id").set_index("widget_id")
    type_dummies = pd.get_dummies(meta["widget_type"], prefix="type")
    sport_dummies = pd.get_dummies(meta["sport"], prefix="sport")
    features = pd.concat([type_dummies, sport_dummies], axis=1).astype(float)
    return features


def test_ground_truth(test_df: pd.DataFrame, min_event_type: str = "interaction") -> dict[int, set[int]]:
    """Ground truth for evaluation: which widgets did each user
    genuinely engage with (interaction or completion, not just a
    passive impression) during the test period."""
    meaningful = test_df[test_df["event_type"].isin(["interaction", "completion"])]
    return meaningful.groupby("user_id")["widget_id"].apply(set).to_dict()
