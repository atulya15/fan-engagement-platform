import snapshotData from "../../data/snapshot.json";

export interface Hero {
  total_users: number;
  total_events: number;
  simulation_months: number;
  avg_stickiness_30d: number;
  median_sessions_per_user: number;
}

export interface RetentionCohortRow {
  cohort_week: string;
  cohort_size: number;
  values: (number | null)[];
}

export interface Retention {
  cohorts: string[];
  weeks: number[];
  grid: RetentionCohortRow[];
}

export interface Funnel {
  steps: string[];
  users_reached: number[];
  pct_of_signups: number[];
  pct_of_previous_step: (number | null)[];
}

export interface Growth {
  weeks: string[];
  new_users: number[];
  returning_users: number[];
  resurrected_users: number[];
  quick_ratio: (number | null)[];
}

export interface ExperimentPrimary {
  metric_a: number;
  metric_b: number;
  diff: number;
  relative_lift_pct: number;
  se: number;
  statistic: number;
  p_value: number;
  ci_low: number;
  ci_high: number;
  alpha: number;
  n_a: number;
  n_b: number;
}

export interface ExperimentDecision {
  recommendation: string;
  reason: string;
  is_significant: boolean;
  is_practical: boolean;
  guardrails_ok: boolean;
}

export interface Experiment {
  name: string;
  primary_metric: string;
  primary: ExperimentPrimary;
  decision: ExperimentDecision;
  guardrail_ok: boolean;
  cuped_variance_reduction_pct: number;
  sequential_peeks: { day: number; p_value: number }[];
  sequential_alphas: { method: string; look: number; alpha_spent: number }[];
}

export interface RecommendationEvalRow {
  method: "cf" | "content" | "hybrid";
  segment: "all" | "warm_only" | "cold_only";
  n_users: number;
  recall_at_10: number;
  ndcg_at_10: number;
}

export interface RecommendationEval {
  summary: RecommendationEvalRow[];
  n_test_users: number;
  n_warm: number;
  n_cold: number;
  catalog_size: number;
}

export interface Snapshot {
  hero: Hero;
  retention: Retention;
  funnel: Funnel;
  growth: Growth;
  experiment: Experiment;
  recommendation_eval: RecommendationEval;
}

export const snapshot = snapshotData as unknown as Snapshot;
