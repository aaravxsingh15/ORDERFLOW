export type Status = "ON TIME" | "AT RISK" | "DELAY LIKELY";
export type Level = "High" | "Medium" | "Low";

export const TRAFFIC = ["Low", "Moderate", "Heavy", "Severe"] as const;
export const WEATHER = ["Clear", "Rain", "Fog", "Hot", "Cold"] as const;
export const AREAS = ["Urban", "Dense Urban", "Suburban"] as const;
export const LOADS = ["Low", "Moderate", "High", "Very High"] as const;
export const EXPERIENCE = ["New", "Moderate", "Experienced"] as const;
export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] as const;

export interface OrderInput {
  order_id: string;
  order_time: string;
  day_of_week: string;
  num_items: number;
  order_value: number;
  prep_time: number;
  restaurant_load: string;
  rider_assignment_delay: number;
  pickup_wait: number;
  distance_km: number;
  traffic_level: string;
  weather: string;
  area_type: string;
  rider_experience: string;
  peak_hour: boolean | null;
  promised_eta: number | null;
  batch_delivery: boolean;
  customer_zone?: string | null;
  restaurant_zone?: string | null;
}

export interface Factor {
  name: string;
  contribution_pct: number;
  minutes: number;
}

export interface Stage {
  key: string;
  label: string;
  minutes: number;
  cumulative: number;
  flag: "primary" | "secondary" | null;
  excess_minutes: number;
}

export interface Influence {
  label: string;
  value: string;
  delta_probability: number;
  influence_pct: number;
  direction: "increases" | "reduces" | "neutral";
}

export interface OrderAnalysis {
  order_id: string;
  status: Status;
  delay_probability: number;
  predicted_delayed: boolean;
  delay_confidence: Level;
  eta: { minutes: number; low: number; high: number; confidence: Level };
  promised_eta: number;
  promised_eta_estimated: boolean;
  expected_delay_minutes: number;
  bottleneck: {
    primary: Factor;
    secondary: Factor | null;
    contributions: { name: string; minutes: number; pct: number }[];
    method: string;
  };
  pipeline: { stages: Stage[]; total_minutes: number };
  explanation: Influence[];
  inputs: Record<string, string | number>;
  warnings: string[];
  delay_rule: string;
  summary: string;
}

export interface BatchOrder {
  order_id: string;
  order_time: string;
  hour: number;
  day_of_week: string;
  num_items: number;
  order_value: number;
  prep_time: number;
  restaurant_load: string;
  rider_assignment_delay: number;
  pickup_wait: number;
  distance_km: number;
  traffic_level: string;
  weather: string;
  area_type: string;
  rider_experience: string;
  peak_hour: number;
  batch_delivery: number;
  promised_eta: number;
  promised_eta_estimated: boolean;
  distance_category: string;
  status: Status;
  delay_probability: number;
  delay_confidence: Level;
  eta_minutes: number;
  primary_bottleneck: string;
  primary_pct: number;
  secondary_bottleneck: string | null;
  secondary_pct: number;
  actual_delivery_time: number | null;
  actual_delayed: number | null;
  outlier_flag: boolean;
}

export interface QualityIssue {
  row: number;
  order_id: string | null;
  code: string;
  reason: string;
}

export interface Quality {
  rows_uploaded: number;
  rows_valid: number;
  rows_removed: number;
  missing_values_fixed: number;
  outliers_flagged: number;
  duplicates_removed: number;
  promised_eta_estimated: number;
  has_actuals: boolean;
  issue_counts: Record<string, number>;
  warnings: string[];
  issues: QualityIssue[];
  issues_truncated: boolean;
}

export interface ClassMetrics {
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  roc_auc: number | null;
}

export interface Summary {
  orders_analysed: number;
  on_time: number;
  at_risk: number;
  delay_likely: number;
  avg_eta_minutes: number;
  avg_delay_probability: number;
  most_common_bottleneck: string;
  worst_delay_window: string | null;
  has_actuals: boolean;
  evaluation: {
    orders_compared: number;
    actual_delay_rate: number;
    classification: ClassMetrics;
    eta: { mae: number; rmse: number; r2: number };
  } | null;
}

export interface GroupRow {
  label: string;
  orders: number;
  avg_delay_probability: number | null;
  actual_delay_rate?: number | null;
  avg_eta?: number | null;
  actual_avg?: number | null;
}

export interface Charts {
  probability_histogram: { bin: string; count: number }[];
  actual_vs_predicted: { actual: number; predicted: number }[];
  status_counts: { status: Status; count: number }[];
  by_traffic: GroupRow[];
  by_restaurant_load: GroupRow[];
  eta_by_distance: GroupRow[];
  bottlenecks: { name: string; count: number }[];
  peak_vs_offpeak: GroupRow[];
  hourly: { hour: number; label: string; orders: number; avg_delay_probability: number | null; actual_delay_rate: number | null }[];
}

export interface BatchResult {
  source: "upload" | "demo";
  filename: string | null;
  quality: Quality;
  summary: Summary;
  charts: Charts;
  orders: BatchOrder[];
  orders_truncated: boolean;
  delay_rule: string;
}

export interface ModelMetricRow {
  model: string;
  primary: boolean;
  [k: string]: number | string | boolean;
}

export interface Importance {
  feature: string;
  label: string;
  importance: number;
}

export interface Metrics {
  dataset: {
    rows_total: number;
    train_rows: number;
    test_rows: number;
    delay_rate: number;
    random_state: number;
    test_size: number;
    sklearn_version: string;
    trained_at: string;
  };
  config: {
    delay_grace_minutes: number;
    on_time_below: number;
    delay_likely_from: number;
    classifier_threshold: number;
    delay_rule: string;
  };
  classifier: {
    model: string;
    features: string[];
    metrics: ClassMetrics;
    confusion_matrix: { tn: number; fp: number; fn: number; tp: number };
    comparison: ModelMetricRow[];
    feature_importance: Importance[];
  };
  regressor: {
    model: string;
    features: string[];
    metrics: { mae: number; rmse: number; r2: number };
    comparison: ModelMetricRow[];
    feature_importance: Importance[];
    range_coverage: number;
    actual_vs_predicted: { actual: number; predicted: number }[];
  };
}
