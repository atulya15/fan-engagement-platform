"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { Experiment } from "@/lib/snapshot";
import { Card } from "./Section";

export function ExperimentCardView({ experiment }: { experiment: Experiment }) {
  const { primary, decision } = experiment;
  const liftPositive = primary.relative_lift_pct >= 0;

  const peekData = experiment.sequential_peeks.map((p) => ({
    day: p.day,
    p_value: p.p_value,
  }));

  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <Card>
        <p className="text-xs font-medium uppercase tracking-wide text-faint">
          {experiment.name}
        </p>
        <p className="mt-1 text-sm text-muted">{experiment.primary_metric}</p>

        <div className="mt-6 flex items-baseline gap-3">
          <span
            className={`text-4xl font-semibold ${
              liftPositive ? "text-[#3fb950]" : "text-[#f47174]"
            }`}
          >
            {liftPositive ? "+" : ""}
            {primary.relative_lift_pct.toFixed(1)}%
          </span>
          <span className="text-sm text-muted">relative lift</span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-faint">p-value</p>
            <p className="num text-foreground">
              {primary.p_value < 0.001 ? "<0.001" : primary.p_value.toFixed(3)}
            </p>
          </div>
          <div>
            <p className="text-faint">95% CI</p>
            <p className="num text-foreground">
              [{primary.ci_low.toFixed(2)}, {primary.ci_high.toFixed(2)}]
            </p>
          </div>
          <div>
            <p className="text-faint">CUPED variance reduction</p>
            <p className="num text-foreground">
              {experiment.cuped_variance_reduction_pct.toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-faint">Sample size</p>
            <p className="num text-foreground">
              {primary.n_a.toLocaleString()} / {primary.n_b.toLocaleString()}
            </p>
          </div>
        </div>

        <div className="mt-6 rounded-lg border border-hairline bg-elevated/40 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-accent">
            Ship decision: {decision.recommendation}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            {decision.reason}
          </p>
        </div>
      </Card>

      <Card>
        <p className="text-sm font-medium text-foreground">
          The peeking problem
        </p>
        <p className="mt-1 text-sm text-muted">
          p-value at each daily look — naive peeking would have called this
          significant on day{" "}
          {peekData.findIndex((p) => p.p_value < 0.05) + 1 || "—"}, well
          before the pre-registered sample size was reached.
        </p>
        <div className="mt-4 h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={peekData}>
              <XAxis
                dataKey="day"
                stroke="var(--color-foreground-faint)"
                fontSize={10}
              />
              <YAxis
                stroke="var(--color-foreground-faint)"
                fontSize={10}
                domain={[0, 1]}
              />
              <Tooltip
                contentStyle={{
                  background: "#0a0a0c",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <ReferenceLine
                y={0.05}
                stroke="#f47174"
                strokeDasharray="4 4"
                label={{
                  value: "α = 0.05",
                  position: "insideTopRight",
                  fill: "#f47174",
                  fontSize: 10,
                }}
              />
              <Line
                type="monotone"
                dataKey="p_value"
                stroke="#818cf8"
                strokeWidth={2}
                dot={{ r: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
