"""
experimentation/analyze.py
============================
Pulls per-user experiment data and runs it through the stats engine
(experimentation/stats.py) for each of the 3 pre-built experiments.

These queries are experiment-specific raw pulls (one row per user, not
pre-aggregated), so they're kept as inline SQL here rather than in
metrics/sql/ -- the metrics/ layer is for reusable, generic business
metrics; this is bespoke per-experiment analysis logic.
"""

import numpy as np
import pandas as pd

from experimentation.stats import (
    achieved_power_two_proportions,
    correct_multiple_comparisons,
    cuped_adjust,
    group_sequential_alpha,
    sample_size_two_proportions,
    sample_size_two_means,
    ship_decision,
    two_proportion_ztest,
    welch_ttest,
)
from metrics.db import run_query

# Channel quality multiplier baked into the generator (generate_data.py)
# -- used here as the CUPED pre-experiment covariate. See cuped_adjust's
# docstring for why a user's OWN pre-period history isn't available for
# these experiments (all three assign at signup) and why a covariate
# known before randomization is the standard workaround.
CHANNEL_QUALITY_MULTIPLIER = {
    "organic": 1.00, "referral": 1.15, "app_store_search": 1.05,
    "paid_social": 0.65, "influencer": 0.55,
}

PRACTICAL_SIGNIFICANCE = {
    "feed": 0.03,       # 3pp absolute lift in Day-7 retention to be worth shipping
    "onboarding": 0.02,  # 2pp absolute lift in first-engagement conversion
    "push": 1.0,         # 1 extra session/user over the window to be worth shipping
}


def _user_level_feed_data() -> pd.DataFrame:
    sql = """
    WITH user_days AS (
        SELECT DISTINCT s.user_id,
               FLOOR(EXTRACT(EPOCH FROM (s.app_open_time - u.signup_date)) / 86400)::int AS day_number
        FROM sessions s JOIN users u ON u.user_id = s.user_id
        WHERE s.app_open_time >= u.signup_date
    ),
    eligible AS (
        SELECT u.user_id, ea.variant, u.acquisition_channel
        FROM users u
        JOIN experiment_assignments ea ON ea.user_id = u.user_id
        JOIN experiments e ON e.experiment_id = ea.experiment_id
                           AND e.experiment_name = 'Personalized Feed vs Chronological'
        WHERE u.signup_date <= (SELECT MAX(app_open_time) FROM sessions) - INTERVAL '7 days'
    ),
    bounded_day7 AS (
        SELECT DISTINCT el.user_id FROM eligible el
        JOIN user_days ud ON ud.user_id = el.user_id AND ud.day_number = 7
    ),
    session_durations AS (
        SELECT user_id, AVG(EXTRACT(EPOCH FROM (app_close_time - app_open_time))) AS avg_duration_sec
        FROM sessions WHERE app_close_time IS NOT NULL
        GROUP BY user_id
    )
    SELECT el.user_id, el.variant, el.acquisition_channel,
           (b.user_id IS NOT NULL)::int AS retained_day7,
           COALESCE(sd.avg_duration_sec, 0) AS avg_session_duration_sec
    FROM eligible el
    LEFT JOIN bounded_day7 b ON b.user_id = el.user_id
    LEFT JOIN session_durations sd ON sd.user_id = el.user_id
    """
    return run_query(sql)


def _user_level_onboarding_data() -> pd.DataFrame:
    sql = """
    WITH eligible AS (
        SELECT u.user_id, ea.variant, u.acquisition_channel
        FROM users u
        JOIN experiment_assignments ea ON ea.user_id = u.user_id
        JOIN experiments e ON e.experiment_id = ea.experiment_id
                           AND e.experiment_name = 'Onboarding Steps Reduction'
    ),
    engaged AS (
        SELECT DISTINCT user_id FROM widget_events WHERE event_type = 'interaction'
    ),
    completion_rate AS (
        SELECT user_id,
               COUNT(*) FILTER (WHERE event_type = 'completion')::numeric
               / NULLIF(COUNT(*) FILTER (WHERE event_type = 'interaction'), 0) AS completion_rate
        FROM widget_events GROUP BY user_id
    )
    SELECT el.user_id, el.variant, el.acquisition_channel,
           (en.user_id IS NOT NULL)::int AS reached_first_engagement,
           COALESCE(cr.completion_rate, 0) AS completion_rate
    FROM eligible el
    LEFT JOIN engaged en ON en.user_id = el.user_id
    LEFT JOIN completion_rate cr ON cr.user_id = el.user_id
    """
    return run_query(sql)


def _user_level_push_data() -> pd.DataFrame:
    sql = """
    WITH eligible AS (
        SELECT u.user_id, ea.variant, u.acquisition_channel
        FROM users u
        JOIN experiment_assignments ea ON ea.user_id = u.user_id
        JOIN experiments e ON e.experiment_id = ea.experiment_id
                           AND e.experiment_name = 'Push Notification Timing'
    ),
    session_stats AS (
        SELECT user_id, COUNT(*) AS session_count,
               AVG(EXTRACT(EPOCH FROM (app_close_time - app_open_time))) AS avg_duration_sec
        FROM sessions WHERE app_close_time IS NOT NULL
        GROUP BY user_id
    )
    SELECT el.user_id, el.variant, el.acquisition_channel,
           COALESCE(ss.session_count, 0) AS session_count,
           COALESCE(ss.avg_duration_sec, 0) AS avg_session_duration_sec
    FROM eligible el
    LEFT JOIN session_stats ss ON ss.user_id = el.user_id
    """
    return run_query(sql)


def analyze_feed_experiment() -> dict:
    """
    Experiment A: Personalized Feed vs Chronological.
    Primary metric: bounded Day-7 retention (binary). Guardrail: average
    session duration (make sure personalization didn't make sessions
    shallower while chasing a return visit).
    """
    df = _user_level_feed_data()
    control = df[df["variant"] == "control"]
    treatment = df[df["variant"] == "treatment"]

    primary = two_proportion_ztest(
        successes_a=int(control["retained_day7"].sum()), n_a=len(control),
        successes_b=int(treatment["retained_day7"].sum()), n_b=len(treatment),
    )

    guardrail = welch_ttest(
        control["avg_session_duration_sec"].to_numpy(),
        treatment["avg_session_duration_sec"].to_numpy(),
    )
    guardrail_ok = guardrail.p_value >= 0.05 or guardrail.diff >= 0  # no significant DROP

    required_n = sample_size_two_proportions(baseline_rate=primary.metric_a,
                                              mde_absolute=PRACTICAL_SIGNIFICANCE["feed"])
    achieved_power = achieved_power_two_proportions(
        baseline_rate=primary.metric_a, observed_lift_absolute=primary.diff, n_per_arm=primary.n_a)

    decision = ship_decision(primary, mde_practical=PRACTICAL_SIGNIFICANCE["feed"],
                              guardrails_ok=guardrail_ok, achieved_power=achieved_power)

    segment_results = _segment_breakdown(df, "acquisition_channel", "retained_day7", binary=True)

    return {
        "name": "Personalized Feed vs Chronological",
        "primary_metric": "bounded_day7_retention",
        "primary": primary,
        "guardrail_metric": "avg_session_duration_sec",
        "guardrail": guardrail,
        "guardrail_ok": guardrail_ok,
        "required_n_per_arm": required_n,
        "achieved_power": achieved_power,
        "decision": decision,
        "segment_results": segment_results,
    }


def analyze_onboarding_experiment() -> dict:
    """
    Experiment B: Onboarding Steps Reduction.
    Primary metric: signup -> first-engagement conversion (binary).
    Guardrail: completion rate (make sure a faster path to engagement
    didn't trade away engagement quality).
    """
    df = _user_level_onboarding_data()
    control = df[df["variant"] == "control"]
    treatment = df[df["variant"] == "treatment"]

    primary = two_proportion_ztest(
        successes_a=int(control["reached_first_engagement"].sum()), n_a=len(control),
        successes_b=int(treatment["reached_first_engagement"].sum()), n_b=len(treatment),
    )

    guardrail = welch_ttest(
        control["completion_rate"].dropna().to_numpy(),
        treatment["completion_rate"].dropna().to_numpy(),
    )
    guardrail_ok = guardrail.p_value >= 0.05 or guardrail.diff >= 0

    required_n = sample_size_two_proportions(baseline_rate=primary.metric_a,
                                              mde_absolute=PRACTICAL_SIGNIFICANCE["onboarding"])
    achieved_power = achieved_power_two_proportions(
        baseline_rate=primary.metric_a, observed_lift_absolute=primary.diff, n_per_arm=primary.n_a)

    decision = ship_decision(primary, mde_practical=PRACTICAL_SIGNIFICANCE["onboarding"],
                              guardrails_ok=guardrail_ok, achieved_power=achieved_power)

    segment_results = _segment_breakdown(df, "acquisition_channel", "reached_first_engagement", binary=True)

    return {
        "name": "Onboarding Steps Reduction",
        "primary_metric": "signup_to_first_engagement_conversion",
        "primary": primary,
        "guardrail_metric": "completion_rate",
        "guardrail": guardrail,
        "guardrail_ok": guardrail_ok,
        "required_n_per_arm": required_n,
        "achieved_power": achieved_power,
        "decision": decision,
        "segment_results": segment_results,
    }


def analyze_push_experiment() -> dict:
    """
    Experiment C: Push Notification Timing (3 arms: morning, evening,
    ml_optimized). Primary comparison is ml_optimized vs. morning
    (morning treated as the pre-existing baseline approach). Primary
    metric: total session count (continuous). Guardrail: average
    session duration. Also demonstrates CUPED variance reduction using
    acquisition-channel quality as the pre-experiment covariate.
    """
    df = _user_level_push_data()
    morning = df[df["variant"] == "morning"]
    ml_opt = df[df["variant"] == "ml_optimized"]
    evening = df[df["variant"] == "evening"]

    primary = welch_ttest(
        morning["session_count"].to_numpy(),
        ml_opt["session_count"].to_numpy(),
    )

    guardrail = welch_ttest(
        morning["avg_session_duration_sec"].to_numpy(),
        ml_opt["avg_session_duration_sec"].to_numpy(),
    )
    guardrail_ok = guardrail.p_value >= 0.05 or guardrail.diff >= 0

    # Cohen's d for the observed effect, used for the sample-size-planning
    # demo (what WOULD we have needed going in, given this effect size).
    pooled_std = np.sqrt((np.var(morning["session_count"], ddof=1) +
                           np.var(ml_opt["session_count"], ddof=1)) / 2)
    cohens_d = primary.diff / pooled_std if pooled_std > 0 else 0
    required_n = sample_size_two_means(effect_size_cohens_d=abs(cohens_d))

    # CUPED: acquisition-channel quality as the pre-experiment covariate
    both = pd.concat([morning, ml_opt])
    x = both["acquisition_channel"].map(CHANNEL_QUALITY_MULTIPLIER).to_numpy()
    y = both["session_count"].to_numpy()
    cuped_result = cuped_adjust(y, x)

    n_a = len(morning)
    y_adj_a = cuped_result["y_adjusted"][:n_a]
    y_adj_b = cuped_result["y_adjusted"][n_a:]
    cuped_test = welch_ttest(y_adj_a, y_adj_b)

    # Multiple comparison correction: testing 2 arm-comparisons against
    # the morning baseline (ml_optimized vs morning, evening vs morning)
    evening_vs_morning = welch_ttest(morning["session_count"].to_numpy(), evening["session_count"].to_numpy())
    correction = correct_multiple_comparisons(
        [primary.p_value, evening_vs_morning.p_value], method="holm")

    # Sequential testing demo: what would 4 evenly-spaced "peeks" at the
    # cumulative data have looked like, vs. the group-sequential
    # threshold that should have been used at each look.
    seq_alphas = group_sequential_alpha(n_looks=4, alpha=0.05, method="obrien_fleming")
    peek_results = _sequential_peek_demo(morning, ml_opt, n_looks=4)

    decision = ship_decision(primary, mde_practical=PRACTICAL_SIGNIFICANCE["push"],
                              guardrails_ok=guardrail_ok, achieved_power=None)

    return {
        "name": "Push Notification Timing",
        "primary_metric": "session_count",
        "primary": primary,
        "guardrail_metric": "avg_session_duration_sec",
        "guardrail": guardrail,
        "guardrail_ok": guardrail_ok,
        "required_n_per_arm": required_n,
        "cohens_d": cohens_d,
        "cuped": cuped_result,
        "cuped_test": cuped_test,
        "evening_vs_morning": evening_vs_morning,
        "multiple_comparison_correction": correction,
        "sequential_alphas": seq_alphas,
        "sequential_peeks": peek_results,
        "decision": decision,
    }


def _segment_breakdown(df: pd.DataFrame, segment_col: str, outcome_col: str, binary: bool) -> list[dict]:
    results = []
    for segment in sorted(df[segment_col].unique()):
        sub = df[df[segment_col] == segment]
        control = sub[sub["variant"] == "control"]
        treatment = sub[sub["variant"] == "treatment"]
        if len(control) < 30 or len(treatment) < 30:
            continue  # too small a slice to draw a reliable conclusion
        if binary:
            r = two_proportion_ztest(
                int(control[outcome_col].sum()), len(control),
                int(treatment[outcome_col].sum()), len(treatment),
            )
        else:
            r = welch_ttest(control[outcome_col].to_numpy(), treatment[outcome_col].to_numpy())
        results.append({"segment": segment, "result": r})
    return results


def _sequential_peek_demo(group_a: pd.DataFrame, group_b: pd.DataFrame, n_looks: int) -> list[dict]:
    """Simulates checking the experiment's results at n_looks evenly
    spaced points using the data's natural accumulation order (by
    user_id, as a stand-in for "users as they arrive over time"), to
    show what a naive analyst peeking at each checkpoint would have
    concluded with an UNADJUSTED alpha=0.05 at every look."""
    a = group_a.sort_values("user_id")["session_count"].to_numpy()
    b = group_b.sort_values("user_id")["session_count"].to_numpy()
    peeks = []
    for i in range(1, n_looks + 1):
        frac = i / n_looks
        n_a, n_b = max(int(len(a) * frac), 2), max(int(len(b) * frac), 2)
        r = welch_ttest(a[:n_a], b[:n_b])
        peeks.append({"look": i, "frac_of_data": frac, "n_a": n_a, "n_b": n_b,
                      "p_value": r.p_value, "naive_significant_at_0.05": r.p_value < 0.05})
    return peeks
