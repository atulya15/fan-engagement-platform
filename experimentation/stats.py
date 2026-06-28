"""
experimentation/stats.py
=========================
The statistical analysis engine: not "run a t-test and check p < 0.05,"
but the actual toolkit a product experimentation team uses to decide
whether to ship a feature.

Covers:
  - Two-sample tests (proportions and means) with confidence intervals,
    not just a p-value.
  - Sample size / power calculation -- answer "how many users do we
    need" BEFORE running an experiment, not just analyze it after.
  - CUPED variance reduction -- using a pre-experiment covariate to
    shrink the variance of the estimate, giving a tighter CI for the
    same sample size.
  - A simplified group-sequential boundary -- the "peeking problem":
    checking results multiple times during an experiment inflates the
    false-positive rate above the nominal alpha unless each look uses a
    stricter threshold than the final look.
  - Multiple comparison correction -- testing several metrics (primary
    + guardrails) at once inflates the chance that AT LEAST ONE shows a
    false positive; Holm's method controls that.
  - A ship/no-ship decision function that combines statistical
    significance, PRACTICAL significance (is the effect big enough to
    matter), and guardrail metrics -- because "p=0.04, ship it?" is
    the wrong question on its own.
"""

from dataclasses import dataclass

import numpy as np
from scipy import stats as scipy_stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize


@dataclass
class TestResult:
    metric_a: float
    metric_b: float
    diff: float
    relative_lift_pct: float
    se: float
    statistic: float
    p_value: float
    ci_low: float
    ci_high: float
    alpha: float
    n_a: int
    n_b: int


def two_proportion_ztest(successes_a: int, n_a: int, successes_b: int, n_b: int,
                          alpha: float = 0.05) -> TestResult:
    """
    Two-sample z-test for a difference in proportions (e.g. retention
    rate, conversion rate), with a normal-approximation confidence
    interval for the difference (b - a).

    Business framing: "a" is control, "b" is treatment. relative_lift_pct
    is the number a PM actually cares about ("retention went up 12%"),
    not the raw percentage-point difference, which can be misleading
    when comparing across metrics with very different baselines.
    """
    p_a, p_b = successes_a / n_a, successes_b / n_b
    diff = p_b - p_a

    # Pooled SE for the hypothesis test (assumes equal proportion under H0)
    p_pool = (successes_a + successes_b) / (n_a + n_b)
    se_pooled = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z_stat = diff / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z_stat)))

    # Unpooled SE for the CI (standard practice: CI uses each arm's own
    # variance, not the H0-pooled variance used for the test statistic)
    se_unpooled = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    z_crit = scipy_stats.norm.ppf(1 - alpha / 2)
    ci_low, ci_high = diff - z_crit * se_unpooled, diff + z_crit * se_unpooled

    relative_lift_pct = (diff / p_a * 100) if p_a > 0 else float("nan")

    return TestResult(p_a, p_b, diff, relative_lift_pct, se_unpooled, z_stat, p_value,
                       ci_low, ci_high, alpha, n_a, n_b)


def welch_ttest(sample_a: np.ndarray, sample_b: np.ndarray, alpha: float = 0.05) -> TestResult:
    """
    Welch's t-test (unequal-variance, not Student's pooled-variance
    t-test) for a difference in means of a continuous metric (e.g.
    sessions per user, session duration). Welch's is the safer default
    because it doesn't assume the two arms have equal variance, which
    a treatment effect can easily break even when the null hypothesis
    of equal MEANS is what's actually being tested.
    """
    mean_a, mean_b = np.mean(sample_a), np.mean(sample_b)
    n_a, n_b = len(sample_a), len(sample_b)
    diff = mean_b - mean_a

    t_stat, p_value = scipy_stats.ttest_ind(sample_b, sample_a, equal_var=False)

    var_a, var_b = np.var(sample_a, ddof=1), np.var(sample_b, ddof=1)
    se = np.sqrt(var_a / n_a + var_b / n_b)
    df = (var_a / n_a + var_b / n_b) ** 2 / (
        (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
    )
    t_crit = scipy_stats.t.ppf(1 - alpha / 2, df)
    ci_low, ci_high = diff - t_crit * se, diff + t_crit * se

    relative_lift_pct = (diff / mean_a * 100) if mean_a != 0 else float("nan")

    return TestResult(mean_a, mean_b, diff, relative_lift_pct, se, t_stat, p_value,
                       ci_low, ci_high, alpha, n_a, n_b)


def sample_size_two_proportions(baseline_rate: float, mde_absolute: float,
                                 alpha: float = 0.05, power: float = 0.8) -> int:
    """
    Required sample size PER ARM to detect an absolute difference of
    `mde_absolute` (minimum detectable effect) from a baseline
    conversion/retention rate, at the given alpha and power.

    This is the calculation that should happen BEFORE running an
    experiment: "we have 5,000 new signups a week and want to detect a
    3pp lift in Day-7 retention from a 20% baseline -- do we have
    enough users, and if so, how many weeks do we need to run this?"
    Running an underpowered experiment and reporting "no significant
    effect" is not the same as "the treatment doesn't work" -- it might
    just mean the experiment was too small to tell the difference.
    """
    effect_size = proportion_effectsize(baseline_rate + mde_absolute, baseline_rate)
    analysis = NormalIndPower()
    n = analysis.solve_power(effect_size=abs(effect_size), alpha=alpha, power=power, ratio=1.0)
    return int(np.ceil(n))


def sample_size_two_means(effect_size_cohens_d: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """
    Required sample size per arm for a continuous metric, given a
    standardized effect size (Cohen's d = mean difference / pooled
    std dev). d=0.2 is a "small" effect, 0.5 "medium", 0.8 "large" --
    most real product experiments target small effects, which is
    exactly why they need large sample sizes to detect reliably.
    """
    analysis = TTestIndPower()
    n = analysis.solve_power(effect_size=effect_size_cohens_d, alpha=alpha, power=power, ratio=1.0)
    return int(np.ceil(n))


def achieved_power_two_proportions(baseline_rate: float, observed_lift_absolute: float,
                                    n_per_arm: int, alpha: float = 0.05) -> float:
    """The flip side of sample-size planning: given the sample size we
    ACTUALLY got and the effect we observed, what power did we have to
    detect it? Low achieved power on a non-significant result means
    "inconclusive," not "no effect" -- an important distinction for the
    ship/no-ship call."""
    effect_size = proportion_effectsize(baseline_rate + observed_lift_absolute, baseline_rate)
    analysis = NormalIndPower()
    return float(analysis.solve_power(effect_size=abs(effect_size), alpha=alpha,
                                       nobs1=n_per_arm, ratio=1.0, power=None))


def cuped_adjust(y: np.ndarray, x: np.ndarray) -> dict:
    """
    CUPED (Controlled-experiment Using Pre-Experiment Data): use a
    covariate `x`, known BEFORE treatment assignment and correlated
    with the outcome `y`, to remove some of y's variance that has
    nothing to do with the treatment -- shrinking the confidence
    interval without needing more users.

        theta = Cov(x, y) / Var(x)
        y_adjusted = y - theta * (x - mean(x))

    y_adjusted has the same mean as y (so the treatment-effect estimate
    is unbiased) but lower variance whenever x and y are correlated.

    In a typical CUPED setup, x is the user's OWN value of the same
    metric measured before the experiment started (e.g. last month's
    session count, before this month's treatment was applied). That
    doesn't exist for THESE experiments -- all three assign users at
    signup, so there's no pre-experiment activity for a brand-new user
    to use as their own covariate. This is a real, common situation
    for new-user experiments, and the standard workaround is the one
    used here: a covariate known before randomization that's correlated
    with the outcome but NOT itself affected by treatment (e.g. the
    user's acquisition-channel quality score). It's a weaker proxy than
    a user's own pre-period history, so the variance reduction is
    smaller -- but the mechanism and the bias-safety property are the
    same, and it generalizes to the (common) cases where pre-period
    history genuinely doesn't exist.
    """
    x_mean = np.mean(x)
    theta = np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)
    y_adjusted = y - theta * (x - x_mean)

    var_before = np.var(y, ddof=1)
    var_after = np.var(y_adjusted, ddof=1)
    var_reduction_pct = 100 * (1 - var_after / var_before) if var_before > 0 else 0.0

    return {
        "theta": theta,
        "y_adjusted": y_adjusted,
        "var_before": var_before,
        "var_after": var_after,
        "var_reduction_pct": var_reduction_pct,
    }


def group_sequential_alpha(n_looks: int, alpha: float = 0.05, method: str = "pocock") -> list[float]:
    """
    The "peeking problem": if you check an experiment's results 5 times
    during its run and stop as soon as p < 0.05 on ANY look, your true
    false-positive rate is much higher than 5% -- each look is another
    chance for noise to cross the threshold. A group-sequential design
    fixes this by using a STRICTER significance threshold at each look,
    so the cumulative false-positive rate across all looks still equals
    the nominal alpha.

    Two classic boundary families:
      - Pocock: roughly the SAME adjusted alpha at every look (simpler,
        but conservative at the final look relative to a fixed-horizon
        test -- you "pay" for the early looks even if you don't use them).
      - O'Brien-Fleming: very strict early, relaxing toward the nominal
        alpha by the final look (better when you mostly care about the
        final decision and only want early stopping for a SLAM-DUNK
        result) -- this is what most production experimentation
        platforms default to.

    These are closed-form APPROXIMATIONS (Pocock's constant-boundary
    approximation; a simplified O'Brien-Fleming spending approximation),
    not the exact recursive numerical integration a production stats
    library (e.g. R's gsDesign) would use -- accurate enough to
    demonstrate the concept and get within a reasonable margin of the
    exact boundary, not precise enough to ship as-is in a real platform.
    """
    if method == "pocock":
        # Approximation: Pocock's constant boundary c_p satisfies
        # alpha = n_looks * 2 * (1 - Phi(c_p)) approximately for small
        # n_looks; solved numerically here rather than table-lookup.
        from scipy.optimize import brentq

        def pocock_eq(c):
            return n_looks * 2 * (1 - scipy_stats.norm.cdf(c)) - alpha

        c_p = brentq(pocock_eq, 0, 6)
        per_look_alpha = 2 * (1 - scipy_stats.norm.cdf(c_p))
        return [per_look_alpha] * n_looks

    elif method == "obrien_fleming":
        # Approximation: O'Brien-Fleming boundary at look k (of n_looks)
        # scales the critical value by sqrt(n_looks / k), so early looks
        # need a much larger z-score (stricter alpha) to stop.
        z_final = scipy_stats.norm.ppf(1 - alpha / 2)
        alphas = []
        for k in range(1, n_looks + 1):
            c_k = z_final * np.sqrt(n_looks / k)
            alphas.append(2 * (1 - scipy_stats.norm.cdf(c_k)))
        return alphas

    raise ValueError(f"Unknown method: {method}")


def correct_multiple_comparisons(p_values: list[float], method: str = "holm") -> dict:
    """
    When testing several metrics at once (a primary metric plus
    guardrails, or a primary metric across multiple segments), the
    chance that AT LEAST ONE shows p < 0.05 purely by chance is higher
    than 5% -- it compounds with each additional test. Holm's method
    (sequential Bonferroni) controls the family-wise error rate while
    being less conservative than a flat Bonferroni correction.
    """
    reject, p_corrected, _, _ = multipletests(p_values, method=method)
    return {
        "raw_p_values": p_values,
        "corrected_p_values": list(p_corrected),
        "reject_null": list(reject),
        "method": method,
    }


def ship_decision(result: TestResult, mde_practical: float, guardrails_ok: bool,
                   achieved_power: float | None = None) -> dict:
    """
    The actual decision function. Combines three independent checks --
    statistical significance is necessary but NOT sufficient on its own:

      1. STATISTICAL significance: is p < alpha?
      2. PRACTICAL significance: is the observed effect at least as
         large as mde_practical (the smallest lift that's worth the
         engineering/maintenance cost of shipping)? A statistically
         significant but tiny effect (e.g. p=0.001, lift=0.1pp) is
         "real" but not worth shipping.
      3. GUARDRAILS: did any metric we're protecting (e.g. didn't tank
         session duration while improving retention) get violated?

    Returns a recommendation string with the reasoning spelled out,
    because "ship: yes/no" without the reasoning is not a defensible
    decision in a real review.
    """
    is_significant = result.p_value < result.alpha
    is_practical = abs(result.diff) >= mde_practical

    if achieved_power is not None and achieved_power < 0.8 and not is_significant:
        recommendation = "inconclusive"
        reason = (f"Not statistically significant (p={result.p_value:.3f}), but achieved power "
                  f"was only {achieved_power:.0%} -- this experiment was underpowered to detect "
                  f"the effect size observed. 'No significant effect' here means 'we couldn't tell,' "
                  f"not 'there's no effect.' Recommend re-running with a larger sample.")
    elif is_significant and is_practical and guardrails_ok:
        recommendation = "ship"
        reason = (f"Significant (p={result.p_value:.3f}) AND practically meaningful "
                  f"(diff={result.diff:.3f} >= MDE={mde_practical}), and no guardrail was violated.")
    elif is_significant and is_practical and not guardrails_ok:
        recommendation = "no-ship"
        reason = (f"Significant and practically meaningful, but a guardrail metric was violated -- "
                  f"the primary lift isn't worth the tradeoff.")
    elif is_significant and not is_practical:
        recommendation = "no-ship"
        reason = (f"Statistically significant (p={result.p_value:.3f}) but the effect "
                  f"(diff={result.diff:.3f}) is below the practical-significance threshold "
                  f"({mde_practical}) -- real, but too small to be worth shipping.")
    else:
        recommendation = "no-ship"
        reason = f"Not statistically significant (p={result.p_value:.3f})."

    return {"recommendation": recommendation, "reason": reason,
            "is_significant": is_significant, "is_practical": is_practical,
            "guardrails_ok": guardrails_ok}
