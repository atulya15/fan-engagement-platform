import { snapshot } from "@/lib/snapshot";
import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { Section } from "@/components/Section";
import { FadeIn } from "@/components/FadeIn";
import { RetentionHeatmap } from "@/components/RetentionHeatmap";
import { FunnelChartView } from "@/components/FunnelChart";
import { GrowthChartView } from "@/components/GrowthChart";
import { ExperimentCardView } from "@/components/ExperimentCard";
import { RecommendationEvalChart } from "@/components/RecommendationEvalChart";
import { RecommendationDemo } from "@/components/RecommendationDemo";
import { Footer } from "@/components/Footer";

export default function Home() {
  const { hero, retention, funnel, growth, experiment, recommendation_eval } =
    snapshot;

  return (
    <main className="flex-1">
      <Nav />
      <Hero hero={hero} />

      <Section
        id="retention"
        eyebrow="Retention"
        title="Weekly cohort retention"
        insight="Blank cells are cohorts too young to have reached that week — censored, not zero. The 28-day rolling retention line (full detail in the dashboard) shows steady stabilization after the first month."
      >
        <FadeIn>
          <RetentionHeatmap retention={retention} />
        </FadeIn>
      </Section>

      <Section
        id="funnels"
        eyebrow="Funnels"
        title="From signup to premium"
        insight="The biggest drop isn't onboarding — it's converting a single engagement into a repeat one. That's the step highlighted in red below."
      >
        <FadeIn>
          <div className="rounded-2xl border border-hairline bg-surface p-6">
            <FunnelChartView funnel={funnel} />
          </div>
        </FadeIn>
      </Section>

      <Section
        id="growth"
        eyebrow="Growth"
        title="New, returning & resurrected users"
        insight="Quick Ratio (new + resurrected ÷ churned) stays above the breakeven line for most of the simulation — the product is net-growing its base, not just retaining it."
      >
        <FadeIn>
          <div className="rounded-2xl border border-hairline bg-surface p-6">
            <GrowthChartView growth={growth} />
          </div>
        </FadeIn>
      </Section>

      <Section
        id="experiment"
        eyebrow="Experimentation"
        title="Push notification timing"
        insight="A full A/B test with CUPED variance reduction, a sequential-peeking demonstration, and an explicit ship/no-ship decision combining statistical and practical significance."
      >
        <FadeIn>
          <ExperimentCardView experiment={experiment} />
        </FadeIn>
      </Section>

      <Section
        id="recommendations"
        eyebrow="Recommendations"
        title="Collaborative filtering vs. content-based vs. hybrid"
        insight={`Pure collaborative filtering goes completely blind on cold-start users (0% recall, ${recommendation_eval.n_cold} of ${recommendation_eval.n_test_users} test users) — the hybrid model degrades gracefully instead. Catalog is ${recommendation_eval.catalog_size} widgets, so absolute Recall@10 values aren't directly comparable to production-scale recommenders; the methodology and the cold-start gap are the point.`}
      >
        <div className="grid gap-6 lg:grid-cols-2">
          <FadeIn>
            <div className="rounded-2xl border border-hairline bg-surface p-6">
              <RecommendationEvalChart evalData={recommendation_eval} />
            </div>
          </FadeIn>
          <FadeIn delay={0.1}>
            <RecommendationDemo />
          </FadeIn>
        </div>
      </Section>

      <Footer />
    </main>
  );
}
