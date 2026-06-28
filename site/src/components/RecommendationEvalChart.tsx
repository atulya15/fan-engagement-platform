"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { RecommendationEval } from "@/lib/snapshot";

const METHOD_LABEL: Record<string, string> = {
  cf: "Collaborative filtering",
  content: "Content-based",
  hybrid: "Hybrid (CF + content)",
};

const METHOD_COLOR: Record<string, string> = {
  cf: "#5e6ad2",
  content: "#3fb950",
  hybrid: "#f4b942",
};

export function RecommendationEvalChart({
  evalData,
}: {
  evalData: RecommendationEval;
}) {
  const segments = ["all", "warm_only", "cold_only"] as const;
  const data = segments.map((segment) => {
    const row: Record<string, number | string> = { segment };
    for (const m of ["cf", "content", "hybrid"]) {
      const match = evalData.summary.find(
        (s) => s.segment === segment && s.method === m
      );
      row[m] = match ? Math.round(match.recall_at_10 * 1000) / 10 : 0;
    }
    return row;
  });

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.06)"
            vertical={false}
          />
          <XAxis
            dataKey="segment"
            tickFormatter={(v: string) =>
              v === "all" ? "All users" : v === "warm_only" ? "Warm users" : "Cold-start users"
            }
            stroke="var(--color-foreground-muted)"
            fontSize={12}
          />
          <YAxis
            unit="%"
            stroke="var(--color-foreground-faint)"
            fontSize={11}
          />
          <Tooltip
            contentStyle={{
              background: "#0a0a0c",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(v, name) => [`${v}%`, METHOD_LABEL[String(name)] ?? String(name)]}
          />
          <Legend
            formatter={(v: string) => METHOD_LABEL[v]}
            wrapperStyle={{ fontSize: 12 }}
          />
          {["cf", "content", "hybrid"].map((m) => (
            <Bar key={m} dataKey={m} fill={METHOD_COLOR[m]} radius={[4, 4, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
