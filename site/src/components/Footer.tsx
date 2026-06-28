const REPO_URL = "https://github.com/atulya15/-fan-engagement-platform";
const DASHBOARD_URL =
  process.env.NEXT_PUBLIC_DASHBOARD_URL ?? REPO_URL;

const STACK = [
  "Next.js 14",
  "TypeScript",
  "Tailwind CSS",
  "Framer Motion",
  "Recharts",
  "FastAPI",
  "PostgreSQL (Supabase)",
  "LightGBM",
  "implicit (ALS)",
];

export function Footer() {
  return (
    <footer className="border-t border-hairline px-6 py-16">
      <div className="mx-auto max-w-5xl">
        <div className="grid gap-10 sm:grid-cols-3">
          <div>
            <p className="text-sm font-medium text-foreground">Stack</p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {STACK.map((s) => (
                <li
                  key={s}
                  className="num rounded-full border border-hairline px-3 py-1 text-xs text-muted"
                >
                  {s}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-sm font-medium text-foreground">Explore further</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <a
                  href={DASHBOARD_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cursor-pointer text-muted transition-colors hover:text-foreground"
                >
                  Full Streamlit dashboard (all 7 tabs) →
                </a>
              </li>
              <li>
                <a
                  href={REPO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cursor-pointer text-muted transition-colors hover:text-foreground"
                >
                  Source code on GitHub →
                </a>
              </li>
            </ul>
          </div>

          <div>
            <p className="text-sm font-medium text-foreground">
              What I&apos;d change at 10x scale
            </p>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              Swap the precomputed snapshot for a metrics warehouse (dbt +
              BigQuery/Snowflake), move retention/funnel SQL to incremental
              materialized views, and replace the synchronous FastAPI
              recommendation training with an offline batch job writing to a
              feature store — the live endpoint should only ever serve a
              lookup, never retrain on request.
            </p>
          </div>
        </div>

        <p className="num mt-12 text-xs text-faint">
          Built as a portfolio project — all data is simulated.
        </p>
      </div>
    </footer>
  );
}
